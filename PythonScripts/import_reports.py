import os
import re
from bs4 import BeautifulSoup
import pymysql
from config import DB_CONFIG

REPORTS_DIR = r"C:\Users\Admin\Desktop\projects\FinanceResearch\CorporateReports"

def clean_number(text):
    if not text:
        return 0.0
    # Szóközök, nem törhető szóközök eltávolítása
    cleaned = text.replace('\xa0', '').replace(' ', '').strip()
    # Speciális magyar/könyvviteli mínuszjelek és nagykötőjelek normalizálása
    cleaned = cleaned.replace('−', '-').replace('–', '-').replace('—', '-')
    if cleaned == '' or cleaned == '-':
        return 0.0
    # Könyvviteli zárójel a negatív számokra: (1000) -> -1000
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def get_clean_key(text):
    """Lecsupaszítja a sorok neveiről a bevezető számozást (a., i., iv., 1., 10., x/1. stb.)"""
    row_name = text.replace('\xa0', ' ').lower()
    row_name = re.sub(r'\s+', ' ', row_name)
    clean_key = re.sub(r'^([a-z0-9ivx]+\/?\d*\.)\s*', '', row_name).strip()
    return clean_key

def parse_address(szekhely_text):
    if not szekhely_text:
        return "Ismeretlen", 0
    pc_match = re.search(r'\b(\d{4})\b', szekhely_text)
    iranyitoszam = int(pc_match.group(1)) if pc_match else 0
    parts = szekhely_text.split()
    varos = "Ismeretlen"
    for i, part in enumerate(parts):
        if re.match(r'^\d{4}$', part) and i + 1 < len(parts):
            varos = parts[i + 1].replace(',', '').strip()
            break
    return varos, iranyitoszam

def parse_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
    data = {}
    text_content = soup.get_text()
    
    if "Hiba történt!" in text_content or "404" in soup.title.get_text():
        return None
    
    filename = os.path.basename(file_path)
    match = re.search(r'(20\d{2})', filename)
    data['et_ev'] = int(match.group(1)) if match else 2016

    firm_name_elem = soup.find('h1', class_='FirmName')
    data['nev'] = firm_name_elem.get_text(strip=True) if firm_name_elem else "Ismeretlen Cég"

    nyilv_match = re.search(r'Nyilvántartási szám:\s*([0-9-]+)', text_content)
    data['nyilvantartasi_szam'] = nyilv_match.group(1) if nyilv_match else "00-00-000000"

    adosz_match = re.search(r'Adószám:\s*([0-9-]+)', text_content)
    data['adoszam'] = adosz_match.group(1) if adosz_match else "00000000-0-00"

    ksh_match = re.search(r'KSH szám:\s*([0-9-]+)', text_content)
    data['ksh_szam'] = ksh_match.group(1) if ksh_match else None

    szekhely_match = re.search(r'Székhely:\s*([^\n]+)', text_content)
    data['szekhely'] = szekhely_match.group(1).strip() if szekhely_match else "Magyarország"
    data['szekhely_varos'], data['szekhely_iranyitoszam'] = parse_address(data['szekhely'])

    letszam_match = re.search(r'Üzleti évben átlagos statisztikai állományi létszám\s*(\d+)', text_content)
    data['atlagos_letszam'] = int(letszam_match.group(1)) if letszam_match else None

    ev = data['et_ev']
    data['uzleti_ev_kezdete'] = f"{ev}-01-01"
    data['uzleti_ev_vege'] = f"{ev}-12-31"

    elfogadas_elem = soup.find('span', id='reportAcceptDate')
    data['elfogadas_idopontja'] = None
    if elfogadas_elem:
        datum_span = elfogadas_elem.find_next_sibling('span', class_='FormData')
        if datum_span:
            datum_text = datum_span.get_text(strip=True).lower()
            honapok = {
                'január': '01', 'február': '02', 'március': '03', 'április': '04',
                'május': '05', 'június': '06', 'július': '07', 'augusztus': '08',
                'szeptember': '09', 'október': '10', 'november': '11', 'december': '12'
            }
            match = re.search(r'(\d{4})\.\s*([a-záéíóöőúüű]+)\s*(\d{1,2})\.', datum_text)
            if match:
                data['elfogadas_idopontja'] = f"{match.group(1)}-{honapok.get(match.group(2), '01')}-{match.group(3).zfill(2)}"

    text_rows = {}
    for table in soup.find_all('table', class_='AttachmentTable'):
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 3:
                targyevi_text = tds[-1].get_text(strip=True)
                clean_key = get_clean_key(tds[1].get_text(separator=' ', strip=True))
                text_rows[clean_key] = clean_number(targyevi_text)

    data['text_rows'] = text_rows
    return data

def main():
    connection = pymysql.connect(
        host=DB_CONFIG['host'], port=DB_CONFIG['port'],
        user=DB_CONFIG['user'], password=DB_CONFIG['password'],
        database=DB_CONFIG['database'], charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
    )

    all_columns = [
        'beszamolo_id', 'eszkozok_osszesen', 'a_befektetett_eszkozok', 'a_i_immaterialis_javak', 
        'a_i_1_alapitas_atszervezes_aktivalt_erteke', 'a_i_2_kiserleti_fejlesztes_aktivalt_erteke',
        'a_i_3_vagyoni_erteku_jogok', 'a_i_4_szellemi_termekek', 'a_i_5_uzleti_vagy_cegertek',
        'a_i_6_immaterialis_javakra_adott_elolegek', 'a_i_7_immaterialis_javak_ertekhelyesbitese',
        'a_ii_targyi_eszkozok', 'a_ii_1_ingatlanok_es_a_kapcsolodo_vagyoni_erteku_jogok',
        'a_ii_2_muszaki_berendezesek_gepek_jarmuvek', 'a_ii_3_egyeb_berendezesek_felszerelesek_jarmuvek',
        'a_ii_4_tenyeszallatok', 'a_ii_5_beruhazasok_felujitasok', 'a_ii_6_beruhazasokra_adott_elolegek',
        'a_ii_7_targyi_eszkozok_ertekhelyesbitese', 'a_iii_befektetett_penzugyi_eszkozok',
        'a_iii_1_tartos_reszesedes_kapcsolt_vallalkozasban', 'a_iii_2_tartosan_adott_kolcson_kapcsolt_vallalkozasban',
        'a_iii_3_tartos_jelentos_tulajdoni_reszesedes', 'a_iii_4_tartosan_adott_kolcson_jelentos_tul_viszonyban',
        'a_iii_5_egyeb_tartos_reszesedes', 'a_iii_6_tartosan_adott_kolcson_egyeb_reszesedesi_viszonyban',
        'a_iii_7_egyeb_tartosan_adott_kolcson', 'a_iii_8_tartos_hitelviszonyt_megtestesito_ertekpapir',
        'a_iii_9_befektetett_penzugyi_eszkozok_ertekhelyesbitese', 'a_iii_10_befektetett_penzugyi_eszkozok_ertekelesi_kulonbozete',
        'a_iv_halasztott_adokoveteles', 'b_forgoeszkozok', 'b_i_keszletek', 'b_i_1_anyagok', 'b_i_2_befejezetlen_termeles_es_felkesz_termekek',
        'b_i_3_novendek_hizo_es_egyeb_allatok', 'b_i_4_kesztermekek', 'b_i_5_aruk', 'b_i_6_keszletekre_adott_elolegek',
        'b_ii_kovetelesek', 'b_ii_1_kovetelesek_aruszallitasbol_szolgaltatasbol_vevok',
        'b_ii_2_kovetelesek_kapcsolt_vallalkozassal_szemben', 'b_ii_3_kovetelesek_jelentos_tulajdoni_reszesedesi_viszonyban',
        'b_ii_4_kovetelesek_egyeb_reszesedesi_viszonyban', 'b_ii_5_valtokovetelesek', 'b_ii_6_egyeb_kovetelesek',
        'b_ii_7_kovetelesek_ertekelesi_kulonbozete', 'b_ii_8_szarmazekos_ugyletek_pozitiv_ertekelesi_kulonbozete',
        'b_iii_ertekpapirok', 'b_iii_1_reszesedes_kapcsolt_vallalkozasban', 'b_iii_2_jelentos_tulajdoni_reszesedes',
        'b_iii_3_egyeb_reszesedes', 'b_iii_4_sajat_reszvenyek_sajat_uzletreszek', 'b_iii_5_forgatasi_celu_hitelviszonyt_megtestesito_ertekpapirok',
        'b_iii_6_ertekpapirok_ertekelesi_kulonbozete', 'b_iv_penzeszkozok', 'b_iv_1_penztar_csekkek', 'b_iv_2_bankbetetek',
        'c_aktiv_idobeli_elhatarolasok', 'c_1_bevetelek_aktiv_idobeli_elhatarolasa', 'c_2_koltsgek_forditasok_aktiv_idobeli_elhatarolasa',
        'c_3_halasztott_raforditasok', 'forrasok_osszesen', 'd_sajat_toke', 'd_i_jegyzett_toke', 'd_i_ebbol_visszavasarolt_tulajdoni_reszesedes',
        'd_ii_jegyzett_de_meg_be_nem_fizetett_toke', 'd_iii_toketartalek', 'd_iv_eredmenytartalek', 'd_v_lekotott_tartalek', 'd_vi_ertekelesi_tartalek',
        'd_vi_1_ertekhelyesbites_ertekelesi_tartaleka', 'd_vi_2_valos_ertekeles_ertekelesi_tartaleka', 'd_vii_adozott_eredmeny',
        'e_celtartalekok', 'e_1_celtartalek_a_varhato_kotelezettsegekre', 'e_2_celtartalek_a_jovobeni_koltsegekre', 'e_3_egyeb_celtartalek',
        'f_kotelezettsegek', 'f_i_hatrasorolt_kotelezettsegek', 'f_i_1_hatrasorolt_kotelezettsegek_kapcsolt_vinnel',
        'f_i_2_hatrasorolt_kotelezettsegek_jelentos_tul_viszonyban', 'f_i_3_hatrasorolt_kotelezettsegek_egyeb_reszesedesi_viszonyban',
        'f_i_4_hatrasorolt_kotelezettsegek_egyeb_gazdalkodoval', 'f_ii_hosszu_lejaratu_kotelezettsegek',
        'f_ii_1_hosszu_lejaratra_kapott_kolcsonok', 'f_ii_2_atvaltoztathato_es_atvaltozo_kotvenyek', 'f_ii_3_tartozasok_kotvenykibocsatasbol',
        'f_ii_4_beruhazasi_es_fejlesztesi_hitelek', 'f_ii_5_egyeb_hosszu_lejaratu_hitelek', 'f_ii_6_tartos_kotelezettsegek_kapcsolt_vinnel',
        'f_ii_7_tartos_kotelezettsegek_jelentos_tul_viszonyban', 'f_ii_8_tartos_kotelezettsegek_egyeb_reszesedesi_viszonyban',
        'f_ii_9_egyeb_hosszu_lejaratu_kotelezettsegek', 'f_ii_10_halasztott_adokotelezettseg', 'f_iii_rovid_lejaratu_kotelezettsegek',
        'f_iii_1_rovid_lejaratu_kolcsonok', 'f_iii_1_ebbol_az_atvaltoztathato_kotvenyek', 'f_iii_2_rovid_lejaratu_hitelek',
        'f_iii_3_vevoktol_kapott_elolegek', 'f_iii_4_kotelezettsegek_aruszallitasbol_szolgal_szallitok',
        'f_iii_5_valtotartozasok', 'f_iii_6_rovid_lejaratu_kotelezettsegek_kapcsolt_vinnel', 'f_iii_7_rovid_lejaratu_kotelezettsegek_jelentos_tul_viszonyban',
        'f_iii_8_rovid_lejaratu_kotelezettsegek_egyeb_reszesedesi', 'f_iii_9_egyeb_rovid_lejaratu_kotelezettsegek',
        'f_iii_10_kotelezettsegek_ertekelesi_kulonbozete', 'f_iii_11_szarmazekos_ugyletek_negativ_ertekelesi_kulonbozete',
        'g_passziv_idobeli_elhatarolasok', 'g_1_bevetelek_passziv_idobeli_elhatarolasa', 'g_2_koltsgek_raforditasok_passziv_idobeli_elhatarolasa',
        'g_3_halasztott_bevetelek', 'ek_01_belfoldi_ertekesites_netto_arbevetele', 'ek_02_exportertekesites_netto_arbevetele', 'ek_i_ertekesites_netto_arbevetele',
        'ek_03_sajat_termelesu_keszletek_allomanyvaltozasa', 'ek_04_sajat_elallitasi_eszkozok_aktivalt_erteke', 'ek_ii_aktivalt_sajat_teljesitmenyek_erteke',
        'ek_iii_egyeb_bevetelek', 'ek_iii_ebbol_visszairt_ertekvesztes', 'ek_05_anyagkoltseg', 'ek_06_igenybe_vett_szolgaltatasok_erteke',
        'ek_07_egyeb_szolgaltatasok_erteke', 'ek_08_eladott_aruk_beszerzesi_erteke', 'ek_09_eladott_kozvetitett_szolgaltatasok_erteke',
        'ek_iv_anyagjellegu_raforditasok', 'ek_10_berkoltseg', 'ek_11_szemelyi_jellegu_egyeb_kifizetesek', 'ek_12_berjarulekok',
        'ek_v_szemelyi_jellegu_raforditasok', 'ek_vi_ertekcsokkenesi_leiras', 'ek_vii_egyeb_raforditasok', 'ek_vii_ebbol_ertekvesztes',
        'ek_a_uzemi_uzleti_tevekenyseg_eredmenye', 'ek_13_kapott_jaro_osztalek_es_reszesedes', 'ek_13_ebbol_kapcsolt_viallatkozastol_kapott',
        'ek_14_reszesedesekbol_szarmazo_bevetelek_arfolyamnyeresek', 'ek_14_ebbol_kapcsolt_viallatkozastol_kapott',
        'ek_15_befektetett_penzugyi_eszkozokbol_szarmazo_bevetelek', 'ek_15_ebbol_kapcsolt_viallatkozastol_kapott',
        'ek_16_egyeb_kapott_jaro_kamatok_es_kamatjellegu_bevetelek', 'ek_16_ebbol_kapcsolt_viallatkozastol_kapott',
        'ek_17_penzugyi_muveletek_egyeb_bevetelek', 'ek_17_ebbol_ertekelesi_kulonbozet', 'ek_viii_penzugyi_muveletek_bevetelek',
        'ek_18_reszesedesekbol_szarmazo_raforditasok_arfolyamveszteségek', 'ek_18_ebbol_kapcsolt_vallalkozasnak_adott',
        'ek_19_befektetett_penzugyi_eszkozok_raforditasai', 'ek_19_ebbol_kapcsolt_vallalkozasnak_adott',
        'ek_20_fizetendo_kamatok_es_kamatjellegu_raforditasok', 'ek_20_ebbol_kapcsolt_vallalkozasnak_adott',
        'ek_21_reszesedesek_ertekpapirok_bankbetetek_ertekvesztese', 'ek_22_penzugyi_muveletek_egyeb_raforditasai',
        'ek_22_ebbol_ertekelesi_kulonbozet', 'ek_ix_penzugyi_muveletek_raforditasai', 'ek_b_penzugyi_muveletek_eredmenye',
        'ek_c_adozas_elotti_eredmeny', 'ek_x_adofizetesi_kotelezettseg', 'ek_x_1_halasztott_adokulonbozet', 'ek_d_adozott_eredmeny'
    ]

    try:
        with connection.cursor() as cursor:
            files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.html')]
            
            for file_name in files:
                file_path = os.path.join(REPORTS_DIR, file_name)
                p = parse_html_file(file_path)
                if not p: continue 
                    
                print(f"{file_name} feldolgozása szöveges motorral...")
                
                cursor.execute("""
                    INSERT INTO cegek (nev, nyilvantartasi_szam, adoszam, ksh_szam, szekhely, szekhely_varos, szekhely_iranyitoszam)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        nev=VALUES(nev), adoszam=VALUES(adoszam), ksh_szam=VALUES(ksh_szam), 
                        szekhely=VALUES(szekhely), szekhely_varos=VALUES(szekhely_varos), szekhely_iranyitoszam=VALUES(szekhely_iranyitoszam);
                """, (p['nev'], p['nyilvantartasi_szam'], p['adoszam'], p['ksh_szam'], p['szekhely'], p['szekhely_varos'], p['szekhely_iranyitoszam']))
                
                cursor.execute("SELECT id FROM cegek WHERE nyilvantartasi_szam = %s", (p['nyilvantartasi_szam'],))
                ceg_id = cursor.fetchone()['id']

                cursor.execute("""
                    INSERT INTO beszamolok (ceg_id, uzleti_ev_kezdete, uzleti_ev_vege, et_ev, penznem, penzegyseg, atlagos_letszam, elfogadas_idopontja)
                    VALUES (%s, %s, %s, %s, 'HUF', 'ezer', %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        atlagos_letszam=VALUES(atlagos_letszam), elfogadas_idopontja=VALUES(elfogadas_idopontja);
                """, (ceg_id, p['uzleti_ev_kezdete'], p['uzleti_ev_vege'], p['et_ev'], p['atlagos_letszam'], p['elfogadas_idopontja']))

                cursor.execute("SELECT id FROM beszamolok WHERE ceg_id = %s AND et_ev = %s", (ceg_id, p['et_ev']))
                beszamolo_id = cursor.fetchone()['id']

                tr = p['text_rows']
                insert_data = {col: 0 for col in all_columns}
                insert_data['beszamolo_id'] = beszamolo_id

                # MÉRLEG FŐCSOPORTOK
                insert_data['a_befektetett_eszkozok'] = tr.get('befektetett eszközök', 0)
                insert_data['a_i_immaterialis_javak'] = tr.get('immateriális javak', 0)
                insert_data['a_ii_targyi_eszkozok'] = tr.get('tárgyi eszközök', 0)
                insert_data['a_iii_befektetett_penzugyi_eszkozok'] = tr.get('befektetett pénzügyi eszközök', 0)
                insert_data['a_iv_halasztott_adokoveteles'] = tr.get('halasztott adókövetelés', 0)
                
                insert_data['b_forgoeszkozok'] = tr.get('forgóeszközök', 0)
                insert_data['b_i_keszletek'] = tr.get('készletek', 0)
                insert_data['b_ii_kovetelesek'] = tr.get('követelések', 0)
                insert_data['b_iii_ertekpapirok'] = tr.get('értékpapírok', 0)
                insert_data['b_iv_penzeszkozok'] = tr.get('pénzeszközök', 0)
                
                insert_data['c_aktiv_idobeli_elhatarolasok'] = tr.get('aktív időbeli elhatárolások', 0)
                insert_data['eszkozok_osszesen'] = tr.get('eszközök (aktívák) összesen', tr.get('eszközök összesen', 0))
                
                insert_data['d_sajat_toke'] = tr.get('saját tőke', 0)
                insert_data['d_i_jegyzett_toke'] = tr.get('jegyzett tőke', 0)
                insert_data['d_ii_jegyzett_de_meg_be_nem_fizetett_toke'] = tr.get('jegyzett, de még be nem fizetett tőke', 0)
                insert_data['d_iii_toketartalek'] = tr.get('tőketartalék', 0)
                insert_data['d_iv_eredmenytartalek'] = tr.get('eredménytartalék', 0)
                insert_data['d_v_lekotott_tartalek'] = tr.get('lekötött tartalék', 0)
                insert_data['d_vi_ertekelesi_tartalek'] = tr.get('értékelési tartalék', 0)
                insert_data['d_vii_adozott_eredmeny'] = tr.get('adózott eredmény', 0)
                
                insert_data['e_celtartalekok'] = tr.get('céltartalékok', 0)
                insert_data['f_kotelezettsegek'] = tr.get('kötelezettségek', 0)
                insert_data['f_i_hatrasorolt_kotelezettsegek'] = tr.get('hátrasorolt kötelezettségek', 0)
                insert_data['f_ii_hosszu_lejaratu_kotelezettsegek'] = tr.get('hosszú lejáratú kötelezettségek', 0)
                insert_data['f_ii_10_halasztott_adokotelezettseg'] = tr.get('halasztott adókötelezettség', 0)
                insert_data['f_iii_rovid_lejaratu_kotelezettsegek'] = tr.get('rövid lejáratú kötelezettségek', 0)
                
                insert_data['g_passziv_idobeli_elhatarolasok'] = tr.get('passzív időbeli elhatárolások', 0)
                insert_data['forrasok_osszesen'] = tr.get('források (passzívák) összesen', tr.get('források összesen', 0))

                # MÉRLEG RÉSZLETEZŐ SOROK (Normál éves beszámolókhoz)
                insert_data['a_i_1_alapitas_atszervezes_aktivalt_erteke'] = tr.get('alapítás-átszervezés aktivált értéke', 0)
                insert_data['a_i_2_kiserleti_fejlesztes_aktivalt_erteke'] = tr.get('kísérleti fejlesztés aktivált értéke', 0)
                insert_data['a_i_3_vagyoni_erteku_jogok'] = tr.get('vagyoni értékű jogok', 0)
                insert_data['a_i_4_szellemi_termekek'] = tr.get('szellemi termékek', 0)
                insert_data['a_i_5_uzleti_vagy_cegertek'] = tr.get('üzleti vagy cégérték', 0)
                insert_data['a_i_6_immaterialis_javakra_adott_elolegek'] = tr.get('immateriális javakra adott előlegek', 0)
                insert_data['a_i_7_immaterialis_javak_ertekhelyesbitese'] = tr.get('immateriális javak értékhelyesbítése', 0)

                insert_data['a_ii_1_ingatlanok_es_a_kapcsolodo_vagyoni_erteku_jogok'] = tr.get('ingatlanok és a kapcsolódó vagyoni értékű jogok', 0)
                insert_data['a_ii_2_muszaki_berendezesek_gepek_jarmuvek'] = tr.get('műszaki berendezések, gépek, járművek', 0)
                insert_data['a_ii_3_egyeb_berendezesek_felszerelesek_jarmuvek'] = tr.get('egyéb berendezések, felszerelések, járművek', 0)
                insert_data['a_ii_4_tenyeszallatok'] = tr.get('tenyészállatok', 0)
                insert_data['a_ii_5_beruhazasok_felujitasok'] = tr.get('beruházások, felújítások', 0)
                insert_data['a_ii_6_beruhazasokra_adott_elolegek'] = tr.get('beruházásokra adott előlegek', 0)
                insert_data['a_ii_7_targyi_eszkozok_ertekhelyesbitese'] = tr.get('tárgyi eszközök értékhelyesbítése', 0)

                insert_data['a_iii_1_tartos_reszesedes_kapcsolt_vallalkozasban'] = tr.get('tartós részesedés kapcsolt vállalkozásban', 0)
                insert_data['a_iii_2_tartosan_adott_kolcson_kapcsolt_vallalkozasban'] = tr.get('tartósan adott kölcsön kapcsolt vállalkozásban', 0)
                insert_data['a_iii_3_tartos_jelentos_tulajdoni_reszesedes'] = tr.get('tartós jelentős tulajdoni részesedés', 0)
                insert_data['a_iii_4_tartosan_adott_kolcson_jelentos_tul_viszonyban'] = tr.get('tartósan adott kölcsön jelentős tulajdoni részesedési viszonyban álló vállalkozásban', tr.get('tartósan adott kölcsön jelentős tulajdoni részesedési viszonyban lévő vállalkozásban', 0))
                insert_data['a_iii_5_egyeb_tartos_reszesedes'] = tr.get('egyéb tartós részesedés', 0)
                insert_data['a_iii_6_tartosan_adott_kolcson_egyeb_reszesedesi_viszonyban'] = tr.get('tartósan adott kölcsön egyéb részesedési viszonyban álló vállalkozásban', tr.get('tartósan adott kölcsön egyéb részesedési viszonyban lévő vállalkozásban', 0))
                insert_data['a_iii_7_egyeb_tartosan_adott_kolcson'] = tr.get('egyéb tartósan adott kölcsön', 0)
                insert_data['a_iii_8_tartos_hitelviszonyt_megtestesito_ertekpapir'] = tr.get('tartós hitelviszonyt megtestesítő értékpapír', 0)
                insert_data['a_iii_9_befektetett_penzugyi_eszkozok_ertekhelyesbitese'] = tr.get('befektetett pénzügyi eszközök értékhelyesbítése', 0)
                insert_data['a_iii_10_befektetett_penzugyi_eszkozok_ertekelesi_kulonbozete'] = tr.get('befektetett pénzügyi eszközök értékelési különbözete', 0)

                insert_data['b_i_1_anyagok'] = tr.get('anyagok', 0)
                insert_data['b_i_2_befejezetlen_termeles_es_felkesz_termekek'] = tr.get('befejezetlen termelés és félkész termékek', 0)
                insert_data['b_i_3_novendek_hizo_es_egyeb_allatok'] = tr.get('növendék-, hízó és egyéb állatok', tr.get('növendék-, hízó- és egyéb állatok', 0))
                insert_data['b_i_4_kesztermekek'] = tr.get('késztermékek', 0)
                insert_data['b_i_5_aruk'] = tr.get('áruk', 0)
                insert_data['b_i_6_keszletekre_adott_elolegek'] = tr.get('készletekre adott előlegek', 0)

                insert_data['b_ii_1_kovetelesek_aruszallitasbol_szolgaltatasbol_vevok'] = tr.get('követelések áruszállításból és szolgáltatásból (vevők)', tr.get('követelések áruszállításból és szolgáltatásból', 0))
                insert_data['b_ii_2_kovetelesek_kapcsolt_vallalkozassal_szemben'] = tr.get('követelések kapcsolt vállalkozással szemben', 0)
                insert_data['b_ii_3_kovetelesek_jelentos_tulajdoni_reszesedesi_viszonyban'] = tr.get('követelések jelentős tulajdoni részesedési viszonyban álló vállalkozással szemben', tr.get('követelések jelentős tulajdoni részesedési viszonyban lévő vállalkozással szemben', 0))
                insert_data['b_ii_4_kovetelesek_egyeb_reszesedesi_viszonyban'] = tr.get('követelések egyéb részesedési viszonyban álló vállalkozással szemben', tr.get('követelések egyéb részesedési viszonyban lévő vállalkozással szemben', 0))
                insert_data['b_ii_5_valtokovetelesek'] = tr.get('váltókövetelések', 0)
                insert_data['b_ii_6_egyeb_kovetelesek'] = tr.get('egyéb követelések', 0)
                insert_data['b_ii_7_kovetelesek_ertekelesi_kulonbozete'] = tr.get('követelések értékelési különbözete', 0)
                insert_data['b_ii_8_szarmazekos_ugyletek_pozitiv_ertekelesi_kulonbozete'] = tr.get('származékos ügyletek pozitív értékelési különbözete', 0)

                insert_data['b_iii_1_reszesedes_kapcsolt_vallalkozasban'] = tr.get('részesedés kapcsolt vállalkozásban', 0)
                insert_data['b_iii_2_jelentos_tulajdoni_reszesedes'] = tr.get('jelentős tulajdoni részesedés', 0)
                insert_data['b_iii_3_egyeb_reszesedes'] = tr.get('egyéb részesedés', 0)
                insert_data['b_iii_4_sajat_reszvenyek_sajat_uzletreszek'] = tr.get('saját részvények, saját üzletrészek', 0)
                insert_data['b_iii_5_forgatasi_celu_hitelviszonyt_megtestesito_ertekpapirok'] = tr.get('forgatási célú hitelviszonyt megtestesítő értékpapírok', 0)
                insert_data['b_iii_6_ertekpapirok_ertekelesi_kulonbozete'] = tr.get('értékpapírok értékelési különbözete', 0)

                insert_data['b_iv_1_penztar_csekkek'] = tr.get('pénztár, csekkek', 0)
                insert_data['b_iv_2_bankbetetek'] = tr.get('bankbetétek', 0)

                insert_data['c_1_bevetelek_aktiv_idobeli_elhatarolasa'] = tr.get('bevételek aktív időbeli elhatárolása', 0)
                insert_data['c_2_koltsgek_forditasok_aktiv_idobeli_elhatarolasa'] = tr.get('költségek, ráfordítások aktív időbeli elhatárolása', 0)
                insert_data['c_3_halasztott_raforditasok'] = tr.get('halasztott ráfordítások', 0)

                insert_data['e_1_celtartalek_a_varhato_kotelezettsegekre'] = tr.get('céltartalék a várható kötelezettségekre', 0)
                insert_data['e_2_celtartalek_a_jovobeni_koltsegekre'] = tr.get('céltartalék a jövőbeni költségekre', 0)
                insert_data['e_3_egyeb_celtartalek'] = tr.get('egyéb céltartalék', 0)

                insert_data['f_i_1_hatrasorolt_kotelezettsegek_kapcsolt_vinnel'] = tr.get('hátrasorolt kötelezettségek kapcsolt vállalkozással szemben', 0)
                insert_data['f_i_2_hatrasorolt_kotelezettsegek_jelentos_tul_viszonyban'] = tr.get('hátrasorolt kötelezettségek jelentős tulajdoni részesedési viszonyban lévő vállalkozással szemben', tr.get('hátrasorolt kötelezettségek jelentős tulajdoni részesedési viszonyban álló vállalkozással szemben', 0))
                insert_data['f_i_3_hatrasorolt_kotelezettsegek_egyeb_reszesedesi_viszonyban'] = tr.get('hátrasorolt kötelezettségek egyéb részesedési viszonyban lévő vállalkozással szemben', tr.get('hátrasorolt kötelezettségek egyéb részesedési viszonyban álló vállalkozással szemben', 0))
                insert_data['f_i_4_hatrasorolt_kotelezettsegek_egyeb_gazdalkodoval'] = tr.get('hátrasorolt kötelezettségek egyéb gazdálkodóval szemben', 0)

                insert_data['f_ii_1_hosszu_lejaratra_kapott_kolcsonok'] = tr.get('hosszú lejáratra kapott kölcsönök', 0)
                insert_data['f_ii_2_atvaltoztathato_es_atvaltozo_kotvenyek'] = tr.get('átváltoztatható és átváltozó kötvények', 0)
                insert_data['f_ii_3_tartozasok_kotvenykibocsatasbol'] = tr.get('tartozások kötvénykibocsátásból', 0)
                insert_data['f_ii_4_beruhazasi_es_fejlesztesi_hitelek'] = tr.get('beruházási és fejlesztési hitelek', 0)
                insert_data['f_ii_5_egyeb_hosszu_lejaratu_hitelek'] = tr.get('egyéb hosszú lejáratú hitelek', 0)
                insert_data['f_ii_6_tartos_kotelezettsegek_kapcsolt_vinnel'] = tr.get('tartós kötelezettségek kapcsolt vállalkozással szemben', 0)
                insert_data['f_ii_7_tartos_kotelezettsegek_jelentos_tul_viszonyban'] = tr.get('tartós kötelezettségek jelentős tulajdoni részesedési viszonyban álló vállalkozással szemben', tr.get('tartós kötelezettségek jelentős tulajdoni részesedési viszonyban lévő vállalkozással szemben', 0))
                insert_data['f_ii_8_tartos_kotelezettsegek_egyeb_reszesedesi_viszonyban'] = tr.get('tartós kötelezettségek egyéb részesedési viszonyban álló vállalkozással szemben', tr.get('tartós kötelezettségek egyéb részesedési viszonyban lévő vállalkozással szemben', 0))
                insert_data['f_ii_9_egyeb_hosszu_lejaratu_kotelezettsegek'] = tr.get('egyéb hosszú lejáratú kötelezettségek', 0)

                insert_data['f_iii_1_rovid_lejaratu_kolcsonok'] = tr.get('rövid lejáratú kölcsönök', 0)
                insert_data['f_iii_2_rovid_lejaratu_hitelek'] = tr.get('rövid lejáratú hitelek', 0)
                insert_data['f_iii_3_vevoktol_kapott_elolegek'] = tr.get('vevőktől kapott előlegek', 0)
                insert_data['f_iii_4_kotelezettsegek_aruszallitasbol_szolgal_szallitok'] = tr.get('kötelezettségek áruszállításból és szolgáltatásból (szállítók)', tr.get('kötelezettségek áruszállításból és szolgáltatásból', 0))
                insert_data['f_iii_5_valtotartozasok'] = tr.get('váltótartozások', 0)
                insert_data['f_iii_6_rovid_lejaratu_kotelezettsegek_kapcsolt_vinnel'] = tr.get('rövid lejáratú kötelezettségek kapcsolt vállalkozással szemben', 0)
                insert_data['f_iii_7_rovid_lejaratu_kotelezettsegek_jelentos_tul_viszonyban'] = tr.get('rövid lejáratú kötelezettségek jelentős tulajdoni részesedési viszonyban álló vállalkozással szemben', tr.get('rövid lejáratú kötelezettségek jelentős tulajdoni részesedési viszonyban lévő vállalkozással szemben', 0))
                insert_data['f_iii_8_rovid_lejaratu_kotelezettsegek_egyeb_reszesedesi'] = tr.get('rövid lejáratú kötelezettségek egyéb részesedési viszonyban álló vállalkozással szemben', tr.get('rövid lejáratú kötelezettségek egyéb részesedési viszonyban lévő vállalkozással szemben', 0))
                insert_data['f_iii_9_egyeb_rovid_lejaratu_kotelezettsegek'] = tr.get('egyéb rövid lejáratú kötelezettségek', 0)
                insert_data['f_iii_10_kotelezettsegek_ertekelesi_kulonbozete'] = tr.get('kötelezettségek értékelési különbözete', 0)
                insert_data['f_iii_11_szarmazekos_ugyletek_negativ_ertekelesi_kulonbozete'] = tr.get('származékos ügyletek negatív értékelési különbözete', 0)

                insert_data['g_1_bevetelek_passziv_idobeli_elhatarolasa'] = tr.get('bevételek passzív időbeli elhatárolása', 0)
                insert_data['g_2_koltsgek_raforditasok_passziv_idobeli_elhatarolasa'] = tr.get('költségek, ráfordítások passzív időbeli elhatárolása', 0)
                insert_data['g_3_halasztott_bevetelek'] = tr.get('halasztott bevételek', 0)

                # EREDMÉNYKIMUTATÁS FŐCSOPORTOK ÉS RÉSZLETEK
                insert_data['ek_i_ertekesites_netto_arbevetele'] = tr.get('értékesítés nettó árbevétele', tr.get('nettó árbevétel', 0))
                insert_data['ek_01_belfoldi_ertekesites_netto_arbevetele'] = tr.get('belföldi értékesítés nettó árbevétele', 0)
                insert_data['ek_02_exportertekesites_netto_arbevetele'] = tr.get('exportértékesítés nettó árbevétele', tr.get('export értékesítés nettó árbevétele', 0))
                
                insert_data['ek_ii_aktivalt_sajat_teljesitmenyek_erteke'] = tr.get('aktivált saját teljesítmények értéke', 0)
                insert_data['ek_03_sajat_termelesu_keszletek_allomanyvaltozasa'] = tr.get('saját termelésű készletek állományváltozása', 0)
                insert_data['ek_04_sajat_elallitasi_eszkozok_aktivalt_erteke'] = tr.get('saját előállítású eszközök aktivált értéke', 0)
                
                insert_data['ek_iii_egyeb_bevetelek'] = tr.get('egyéb bevételek', 0)
                insert_data['ek_iv_anyagjellegu_raforditasok'] = tr.get('anyagjellegű ráfordítások', 0)
                insert_data['ek_05_anyagkoltseg'] = tr.get('anyagköltség', 0)
                insert_data['ek_06_igenybe_vett_szolgaltatasok_erteke'] = tr.get('igénybe vett szolgáltatások értéke', 0)
                insert_data['ek_07_egyeb_szolgaltatasok_erteke'] = tr.get('egyéb szolgáltatások értéke', 0)
                insert_data['ek_08_eladott_aruk_beszerzesi_erteke'] = tr.get('eladott áruk beszerzési értéke', 0)
                insert_data['ek_09_eladott_kozvetitett_szolgaltatasok_erteke'] = tr.get('eladott (közvetített) szolgáltatások értéke', tr.get('eladott közvetített szolgáltatások értéke', 0))
                
                insert_data['ek_v_szemelyi_jellegu_raforditasok'] = tr.get('személyi jellegű ráfordítások', 0)
                insert_data['ek_10_berkoltseg'] = tr.get('bérköltség', 0)
                insert_data['ek_11_szemelyi_jellegu_egyeb_kifizetesek'] = tr.get('személyi jellegű egyéb kifizetések', 0)
                insert_data['ek_12_berjarulekok'] = tr.get('bérjárulékok', 0)
                
                insert_data['ek_vi_ertekcsokkenesi_leiras'] = tr.get('értékcsökkenési leírás', 0)
                insert_data['ek_vii_egyeb_raforditasok'] = tr.get('egyéb ráfordítások', 0)
                insert_data['ek_a_uzemi_uzleti_tevekenyseg_eredmenye'] = tr.get('üzemi (üzleti) tevékenység eredménye', 0)
                insert_data['ek_viii_penzugyi_muveletek_bevetelek'] = tr.get('pénzügyi műveletek bevételei', tr.get('pénzügyi műveletek bevételek', 0))
                insert_data['ek_ix_penzugyi_muveletek_raforditasai'] = tr.get('pénzügyi műveletek ráfordításai', 0)
                insert_data['ek_b_penzugyi_muveletek_eredmenye'] = tr.get('pénzügyi műveletek eredménye', 0)
                insert_data['ek_c_adozas_elotti_eredmeny'] = tr.get('adózás előtti eredmény', 0)
                insert_data['ek_x_adofizetesi_kotelezettseg'] = tr.get('adófizetési kötelezettség', 0)
                insert_data['ek_x_1_halasztott_adokulonbozet'] = tr.get('halasztott adókülönbözet', 0)
                
                insert_data['ek_d_adozott_eredmeny'] = tr.get('adózott eredmény', insert_data['d_vii_adozott_eredmeny'])

                columns_str = ', '.join(insert_data.keys())
                placeholders_str = ', '.join(['%s'] * len(insert_data))
                update_parts = [f"{col}=VALUES({col})" for col in insert_data.keys() if col != 'beszamolo_id']
                update_str = ', '.join(update_parts)

                sql = f"""
                    INSERT INTO beszamolo_adatok ({columns_str})
                    VALUES ({placeholders_str})
                    ON DUPLICATE KEY UPDATE {update_str};
                """
                cursor.execute(sql, tuple(insert_data.values()))

        connection.commit()
        print("\nMinden cég adatai 100%-ban szöveges szótárral feltöltve!")

    except Exception as e:
        connection.rollback()
        import traceback
        traceback.print_exc()
        print("Hiba történt a folyamat során:", e)
    finally:
        connection.close()

if __name__ == '__main__':
    main()