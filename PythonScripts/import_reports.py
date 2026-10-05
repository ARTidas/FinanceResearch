import os
import re
from bs4 import BeautifulSoup
import pymysql
from config import DB_CONFIG

REPORTS_DIR = r"C:\Users\Admin\Desktop\projects\FinanceResearch\CorporateReports" # Átírhatod a saját mappádra!

def clean_number(text):
    if not text:
        return 0.0
    cleaned = text.replace('\xa0', '').replace(' ', '').strip()
    if cleaned == '' or cleaned == '-':
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

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
    
    # Hibaoldalak kiszűrése (ha mégis lenne a mappában)
    if "Hiba történt!" in text_content or "404" in soup.title.get_text():
        return None
    
    # Év kivonása bárhonnan a fájlnévből, ahol van 4 számjegy (pl. dal_2021.html -> 2021)
    filename = os.path.basename(file_path)
    match = re.search(r'(20\d{2})', filename)
    data['et_ev'] = int(match.group(1)) if match else 2016
    
    data['is_egyszerusitett'] = "Egyszerűsített éves beszámoló" in text_content

    firm_name_elem = soup.find('h1', class_='FirmName')
    data['nev'] = firm_name_elem.get_text(strip=True) if firm_name_elem else "Ismeretlen Cég"

    nyilv_match = re.search(r'Nyilvántartási szám:\s*([0-9-]+)', text_content)
    data['nyilvantartasi_szam'] = nyilv_match.group(1) if nyilv_match else "00-00-000000"

    adosz_match = re.search(r'Adószám:\s*([0-9-]+)', text_content)
    data['adoszam'] = adosz_match.group(1) if adosz_match else "00000000-0-00"

    ksh_match = re.search(r'KSH szám:\s*([0-9-]+)', text_content)
    data['ksh_szam'] = ksh_match.group(1) if ksh_match else None

    szekhely_match = re.search(r'Székhely:\s*([^\n]+)', text_content)
    if szekhely_match:
        data['szekhely'] = szekhely_match.group(1).strip()
    else:
        data['szekhely'] = "Magyarország"
        
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
                ev_elf = match.group(1)
                honap_nev = match.group(2)
                nap = match.group(3).zfill(2)
                honap = honapok.get(honap_nev, '01')
                data['elfogadas_idopontja'] = f"{ev_elf}-{honap}-{nap}"

    table_rows = {}
    current_table_type = None
    
    for table in soup.find_all('table', class_='AttachmentTable'):
        table_text = table.get_text()
        if "MÉRLEGE" in table_text:
            current_table_type = "MERLEG"
        elif "EREDMÉNYKIMUTATÁSA" in table_text:
            current_table_type = "EREDMENYKIMUTATAS"
            
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 3:
                sorszam_text = tds[0].get_text(strip=True)
                targyevi_text = tds[-1].get_text(strip=True)
                key = f"{current_table_type}_{sorszam_text}"
                table_rows[key] = clean_number(targyevi_text)

    data['table_rows'] = table_rows
    return data

def main():
    connection = pymysql.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    # Az SQL séma szerinti összes oszlop (alapértelmezetten 0-val töltjük fel)
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
        'a_iv_halasztott_adokoveteles',
        'b_forgoeszkozok', 'b_i_keszletek', 'b_i_1_anyagok', 'b_i_2_befejezetlen_termeles_es_felkesz_termekek',
        'b_i_3_novendek_hizo_es_egyeb_allatok', 'b_i_4_kesztermekek', 'b_i_5_aruk', 'b_i_6_keszletekre_adott_elolegek',
        'b_ii_kovetelesek', 'b_ii_1_kovetelesek_aruszallitasbol_szolgaltatasbol_vevok',
        'b_ii_2_kovetelesek_kapcsolt_vallalkozassal_szemben', 'b_ii_3_kovetelesek_jelentos_tulajdoni_reszesedesi_viszonyban',
        'b_ii_4_kovetelesek_egyeb_reszesedesi_viszonyban', 'b_ii_5_valtokovetelesek', 'b_ii_6_egyeb_kovetelesek',
        'b_ii_7_kovetelesek_ertekelesi_kulonbozete', 'b_ii_8_szarmazekos_ugyletek_pozitiv_ertekelesi_kulonbozete',
        'b_iii_ertekpapirok', 'b_iii_1_reszesedes_kapcsolt_vallalkozasban', 'b_iii_2_jelentos_tulajdoni_reszesedes',
        'b_iii_3_egyeb_reszesedes', 'b_iii_4_sajat_reszvenyek_sajat_uzletreszek', 'b_iii_5_forgatasi_celu_hitelviszonyt_megtestesito_ertekpapirok',
        'b_iii_6_ertekpapirok_ertekelesi_kulonbozete', 'b_iv_penzeszkozok', 'b_iv_1_penztar_csekkek', 'b_iv_2_bankbetetek',
        'c_aktiv_idobeli_elhatarolasok', 'c_1_bevetelek_aktiv_idobeli_elhatarolasa', 'c_2_koltsgek_forditasok_aktiv_idobeli_elhatarolasa',
        'c_3_halasztott_raforditasok',
        'forrasok_osszesen',
        'd_sajat_toke', 'd_i_jegyzett_toke', 'd_i_ebbol_visszavasarolt_tulajdoni_reszesedes', 'd_ii_jegyzett_de_meg_be_nem_fizetett_toke',
        'd_iii_toketartalek', 'd_iv_eredmenytartalek', 'd_v_lekotott_tartalek', 'd_vi_ertekelesi_tartalek',
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
        'g_3_halasztott_bevetelek',
        'ek_01_belfoldi_ertekesites_netto_arbevetele', 'ek_02_exportertekesites_netto_arbevetele', 'ek_i_ertekesites_netto_arbevetele',
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
            # Csak azokra a html fájlokra figyelünk, amelyek formátuma megfelel a letöltötteknek
            files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.html')]
            
            for file_name in files:
                file_path = os.path.join(REPORTS_DIR, file_name)
                
                p = parse_html_file(file_path)
                if not p:
                    continue # Hibaoldal ugrása
                    
                print(f"{file_name} feldolgozása...")
                
                # Cég beszúrása / Frissítése
                cursor.execute("""
                    INSERT INTO cegek (nev, nyilvantartasi_szam, adoszam, ksh_szam, szekhely, szekhely_varos, szekhely_iranyitoszam)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        nev=VALUES(nev), adoszam=VALUES(adoszam), ksh_szam=VALUES(ksh_szam), 
                        szekhely=VALUES(szekhely), szekhely_varos=VALUES(szekhely_varos), szekhely_iranyitoszam=VALUES(szekhely_iranyitoszam);
                """, (
                    p['nev'], p['nyilvantartasi_szam'], p['adoszam'], p['ksh_szam'],
                    p['szekhely'], p['szekhely_varos'], p['szekhely_iranyitoszam']
                ))
                
                cursor.execute("SELECT id FROM cegek WHERE nyilvantartasi_szam = %s", (p['nyilvantartasi_szam'],))
                ceg_id = cursor.fetchone()['id']

                # Beszámoló fejlécének beszúrása
                cursor.execute("""
                    INSERT INTO beszamolok (ceg_id, uzleti_ev_kezdete, uzleti_ev_vege, et_ev, penznem, penzegyseg, atlagos_letszam, elfogadas_idopontja)
                    VALUES (%s, %s, %s, %s, 'HUF', 'ezer', %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        atlagos_letszam=VALUES(atlagos_letszam), elfogadas_idopontja=VALUES(elfogadas_idopontja);
                """, (
                    ceg_id, p['uzleti_ev_kezdete'], p['uzleti_ev_vege'], p['et_ev'],
                    p['atlagos_letszam'], p['elfogadas_idopontja']
                ))

                cursor.execute("SELECT id FROM beszamolok WHERE ceg_id = %s AND et_ev = %s", (ceg_id, p['et_ev']))
                beszamolo_id = cursor.fetchone()['id']

                r = p['table_rows']
                ev = p['et_ev']
                
                # Kezdetben minden mezőt 0-ra állítunk
                insert_data = {col: 0 for col in all_columns}
                insert_data['beszamolo_id'] = beszamolo_id

                if p['is_egyszerusitett']:
                    # EGYSZERŰSÍTETT BONTÁS (Pl: Caffe Dal)
                    o_m = 1 if ev >= 2024 else 0  # Mérleg eltolás
                    o_e = 1 if ev >= 2024 else 0  # Eredménykimutatás eltolás
                    
                    insert_data['a_befektetett_eszkozok'] = r.get('MERLEG_002.', 0)
                    insert_data['a_i_immaterialis_javak'] = r.get('MERLEG_003.', 0)
                    insert_data['a_ii_targyi_eszkozok'] = r.get('MERLEG_004.', 0)
                    insert_data['a_iii_befektetett_penzugyi_eszkozok'] = r.get('MERLEG_005.', 0)
                    insert_data['a_iv_halasztott_adokoveteles'] = r.get('MERLEG_006.', 0) if ev >= 2024 else 0
                    
                    insert_data['b_forgoeszkozok'] = r.get(f'MERLEG_{6 + o_m:03d}.', 0)
                    insert_data['b_i_keszletek'] = r.get(f'MERLEG_{7 + o_m:03d}.', 0)
                    insert_data['b_ii_kovetelesek'] = r.get(f'MERLEG_{8 + o_m:03d}.', 0)
                    insert_data['b_iii_ertekpapirok'] = r.get(f'MERLEG_{9 + o_m:03d}.', 0)
                    insert_data['b_iv_penzeszkozok'] = r.get(f'MERLEG_{10 + o_m:03d}.', 0)
                    
                    insert_data['c_aktiv_idobeli_elhatarolasok'] = r.get(f'MERLEG_{11 + o_m:03d}.', 0)
                    insert_data['eszkozok_osszesen'] = r.get(f'MERLEG_{12 + o_m:03d}.', 0)
                    
                    insert_data['d_sajat_toke'] = r.get(f'MERLEG_{14 + o_m:03d}.', 0)
                    insert_data['d_i_jegyzett_toke'] = r.get(f'MERLEG_{15 + o_m:03d}.', 0)
                    insert_data['d_ii_jegyzett_de_meg_be_nem_fizetett_toke'] = r.get(f'MERLEG_{16 + o_m:03d}.', 0)
                    insert_data['d_iii_toketartalek'] = r.get(f'MERLEG_{17 + o_m:03d}.', 0)
                    insert_data['d_iv_eredmenytartalek'] = r.get(f'MERLEG_{18 + o_m:03d}.', 0)
                    insert_data['d_v_lekotott_tartalek'] = r.get(f'MERLEG_{19 + o_m:03d}.', 0)
                    insert_data['d_vi_ertekelesi_tartalek'] = r.get(f'MERLEG_{20 + o_m:03d}.', 0)
                    insert_data['d_vii_adozott_eredmeny'] = r.get(f'MERLEG_{21 + o_m:03d}.', 0)
                    
                    insert_data['e_celtartalekok'] = r.get(f'MERLEG_{22 + o_m:03d}.', 0)
                    insert_data['f_kotelezettsegek'] = r.get(f'MERLEG_{23 + o_m:03d}.', 0)
                    insert_data['f_i_hatrasorolt_kotelezettsegek'] = r.get(f'MERLEG_{24 + o_m:03d}.', 0)
                    insert_data['f_ii_hosszu_lejaratu_kotelezettsegek'] = r.get(f'MERLEG_{25 + o_m:03d}.', 0)
                    
                    
                    insert_data['f_iii_rovid_lejaratu_kotelezettsegek'] = r.get(f'MERLEG_{26 + o_m:03d}.', 0)
                    
                    # Az egyszerűsített mérlegben 2024-től sincs Halasztott adókötelezettség sor
                    insert_data['f_ii_10_halasztott_adokotelezettseg'] = 0  
                    
                    # Emiatt a passzívák eltolása (o_m) pontosan egyezik az aktívákéval
                    insert_data['g_passziv_idobeli_elhatarolasok'] = r.get(f'MERLEG_{27 + o_m:03d}.', 0)
                    insert_data['forrasok_osszesen'] = r.get(f'MERLEG_{28 + o_m:03d}.', 0)
                    
                    insert_data['ek_i_ertekesites_netto_arbevetele'] = r.get('EREDMENYKIMUTATAS_001.', 0)

                    
                    
                    insert_data['ek_ii_aktivalt_sajat_teljesitmenyek_erteke'] = r.get('EREDMENYKIMUTATAS_002.', 0)
                    insert_data['ek_iii_egyeb_bevetelek'] = r.get('EREDMENYKIMUTATAS_003.', 0)
                    insert_data['ek_iv_anyagjellegu_raforditasok'] = r.get('EREDMENYKIMUTATAS_004.', 0)
                    insert_data['ek_v_szemelyi_jellegu_raforditasok'] = r.get('EREDMENYKIMUTATAS_005.', 0)
                    insert_data['ek_vi_ertekcsokkenesi_leiras'] = r.get('EREDMENYKIMUTATAS_006.', 0)
                    insert_data['ek_vii_egyeb_raforditasok'] = r.get('EREDMENYKIMUTATAS_007.', 0)
                    insert_data['ek_a_uzemi_uzleti_tevekenyseg_eredmenye'] = r.get('EREDMENYKIMUTATAS_008.', 0)
                    insert_data['ek_viii_penzugyi_muveletek_bevetelek'] = r.get('EREDMENYKIMUTATAS_009.', 0)
                    insert_data['ek_ix_penzugyi_muveletek_raforditasai'] = r.get('EREDMENYKIMUTATAS_010.', 0)
                    insert_data['ek_b_penzugyi_muveletek_eredmenye'] = r.get('EREDMENYKIMUTATAS_011.', 0)
                    insert_data['ek_c_adozas_elotti_eredmeny'] = r.get('EREDMENYKIMUTATAS_012.', 0)
                    insert_data['ek_x_adofizetesi_kotelezettseg'] = r.get('EREDMENYKIMUTATAS_013.', 0)
                    insert_data['ek_x_1_halasztott_adokulonbozet'] = r.get('EREDMENYKIMUTATAS_014.', 0) if ev >= 2024 else 0
                    insert_data['ek_d_adozott_eredmeny'] = r.get(f'EREDMENYKIMUTATAS_{14 + o_e:03d}.', 0)

                else:
                    # NORMÁL BONTÁS (Pl: Grand Tokaj)
                    off1 = 1 if ev >= 2023 else 0
                    off2 = 2 if ev >= 2023 else 0
                    off3 = 1 if ev >= 2023 else 0
                    
                    insert_data['a_befektetett_eszkozok'] = r.get('MERLEG_002.', 0)
                    insert_data['a_i_immaterialis_javak'] = r.get('MERLEG_003.', 0)
                    insert_data['a_i_1_alapitas_atszervezes_aktivalt_erteke'] = r.get('MERLEG_004.', 0)
                    insert_data['a_i_2_kiserleti_fejlesztes_aktivalt_erteke'] = r.get('MERLEG_005.', 0)
                    insert_data['a_i_3_vagyoni_erteku_jogok'] = r.get('MERLEG_006.', 0)
                    insert_data['a_i_4_szellemi_termekek'] = r.get('MERLEG_007.', 0)
                    insert_data['a_i_5_uzleti_vagy_cegertek'] = r.get('MERLEG_008.', 0)
                    insert_data['a_i_6_immaterialis_javakra_adott_elolegek'] = r.get('MERLEG_009.', 0)
                    insert_data['a_i_7_immaterialis_javak_ertekhelyesbitese'] = r.get('MERLEG_010.', 0)
                    insert_data['a_ii_targyi_eszkozok'] = r.get('MERLEG_011.', 0)
                    insert_data['a_ii_1_ingatlanok_es_a_kapcsolodo_vagyoni_erteku_jogok'] = r.get('MERLEG_012.', 0)
                    insert_data['a_ii_2_muszaki_berendezesek_gepek_jarmuvek'] = r.get('MERLEG_013.', 0)
                    insert_data['a_ii_3_egyeb_berendezesek_felszerelesek_jarmuvek'] = r.get('MERLEG_014.', 0)
                    insert_data['a_ii_4_tenyeszallatok'] = r.get('MERLEG_015.', 0)
                    insert_data['a_ii_5_beruhazasok_felujitasok'] = r.get('MERLEG_016.', 0)
                    insert_data['a_ii_6_beruhazasokra_adott_elolegek'] = r.get('MERLEG_017.', 0)
                    insert_data['a_ii_7_targyi_eszkozok_ertekhelyesbitese'] = r.get('MERLEG_018.', 0)
                    insert_data['a_iii_befektetett_penzugyi_eszkozok'] = r.get('MERLEG_019.', 0)
                    insert_data['a_iii_1_tartos_reszesedes_kapcsolt_vallalkozasban'] = r.get('MERLEG_020.', 0)
                    insert_data['a_iii_2_tartosan_adott_kolcson_kapcsolt_vallalkozasban'] = r.get('MERLEG_021.', 0)
                    insert_data['a_iii_3_tartos_jelentos_tulajdoni_reszesedes'] = r.get('MERLEG_022.', 0)
                    insert_data['a_iii_4_tartosan_adott_kolcson_jelentos_tul_viszonyban'] = r.get('MERLEG_023.', 0)
                    insert_data['a_iii_5_egyeb_tartos_reszesedes'] = r.get('MERLEG_024.', 0)
                    insert_data['a_iii_6_tartosan_adott_kolcson_egyeb_reszesedesi_viszonyban'] = r.get('MERLEG_025.', 0)
                    insert_data['a_iii_7_egyeb_tartosan_adott_kolcson'] = r.get('MERLEG_026.', 0)
                    insert_data['a_iii_8_tartos_hitelviszonyt_megtestesito_ertekpapir'] = r.get('MERLEG_027.', 0)
                    insert_data['a_iii_9_befektetett_penzugyi_eszkozok_ertekhelyesbitese'] = r.get('MERLEG_028.', 0)
                    insert_data['a_iii_10_befektetett_penzugyi_eszkozok_ertekelesi_kulonbozete'] = r.get('MERLEG_029.', 0)
                    
                    insert_data['a_iv_halasztott_adokoveteles'] = r.get('MERLEG_030.', 0) if ev >= 2023 else 0
                    
                    insert_data['b_forgoeszkozok'] = r.get(f'MERLEG_{30 + off1:03d}.', 0)
                    insert_data['b_i_keszletek'] = r.get(f'MERLEG_{31 + off1:03d}.', 0)
                    insert_data['b_i_1_anyagok'] = r.get(f'MERLEG_{32 + off1:03d}.', 0)
                    insert_data['b_i_2_befejezetlen_termeles_es_felkesz_termekek'] = r.get(f'MERLEG_{33 + off1:03d}.', 0)
                    insert_data['b_i_3_novendek_hizo_es_egyeb_allatok'] = r.get(f'MERLEG_{34 + off1:03d}.', 0)
                    insert_data['b_i_4_kesztermekek'] = r.get(f'MERLEG_{35 + off1:03d}.', 0)
                    insert_data['b_i_5_aruk'] = r.get(f'MERLEG_{36 + off1:03d}.', 0)
                    insert_data['b_i_6_keszletekre_adott_elolegek'] = r.get(f'MERLEG_{37 + off1:03d}.', 0)
                    insert_data['b_ii_kovetelesek'] = r.get(f'MERLEG_{38 + off1:03d}.', 0)
                    insert_data['b_ii_1_kovetelesek_aruszallitasbol_szolgaltatasbol_vevok'] = r.get(f'MERLEG_{39 + off1:03d}.', 0)
                    insert_data['b_ii_2_kovetelesek_kapcsolt_vallalkozassal_szemben'] = r.get(f'MERLEG_{40 + off1:03d}.', 0)
                    insert_data['b_ii_3_kovetelesek_jelentos_tulajdoni_reszesedesi_viszonyban'] = r.get(f'MERLEG_{41 + off1:03d}.', 0)
                    insert_data['b_ii_4_kovetelesek_egyeb_reszesedesi_viszonyban'] = r.get(f'MERLEG_{42 + off1:03d}.', 0)
                    insert_data['b_ii_5_valtokovetelesek'] = r.get(f'MERLEG_{43 + off1:03d}.', 0)
                    insert_data['b_ii_6_egyeb_kovetelesek'] = r.get(f'MERLEG_{44 + off1:03d}.', 0)
                    insert_data['b_ii_7_kovetelesek_ertekelesi_kulonbozete'] = r.get(f'MERLEG_{45 + off1:03d}.', 0)
                    insert_data['b_ii_8_szarmazekos_ugyletek_pozitiv_ertekelesi_kulonbozete'] = r.get(f'MERLEG_{46 + off1:03d}.', 0)
                    insert_data['b_iii_ertekpapirok'] = r.get(f'MERLEG_{47 + off1:03d}.', 0)
                    insert_data['b_iii_1_reszesedes_kapcsolt_vallalkozasban'] = r.get(f'MERLEG_{48 + off1:03d}.', 0)
                    insert_data['b_iii_2_jelentos_tulajdoni_reszesedes'] = r.get(f'MERLEG_{49 + off1:03d}.', 0)
                    insert_data['b_iii_3_egyeb_reszesedes'] = r.get(f'MERLEG_{50 + off1:03d}.', 0)
                    insert_data['b_iii_4_sajat_reszvenyek_sajat_uzletreszek'] = r.get(f'MERLEG_{51 + off1:03d}.', 0)
                    insert_data['b_iii_5_forgatasi_celu_hitelviszonyt_megtestesito_ertekpapirok'] = r.get(f'MERLEG_{52 + off1:03d}.', 0)
                    insert_data['b_iii_6_ertekpapirok_ertekelesi_kulonbozete'] = r.get(f'MERLEG_{53 + off1:03d}.', 0)
                    insert_data['b_iv_penzeszkozok'] = r.get(f'MERLEG_{54 + off1:03d}.', 0)
                    insert_data['b_iv_1_penztar_csekkek'] = r.get(f'MERLEG_{55 + off1:03d}.', 0)
                    insert_data['b_iv_2_bankbetetek'] = r.get(f'MERLEG_{56 + off1:03d}.', 0)
                    insert_data['c_aktiv_idobeli_elhatarolasok'] = r.get(f'MERLEG_{57 + off1:03d}.', 0)
                    insert_data['c_1_bevetelek_aktiv_idobeli_elhatarolasa'] = r.get(f'MERLEG_{58 + off1:03d}.', 0)
                    insert_data['c_2_koltsgek_forditasok_aktiv_idobeli_elhatarolasa'] = r.get(f'MERLEG_{59 + off1:03d}.', 0)
                    insert_data['c_3_halasztott_raforditasok'] = r.get(f'MERLEG_{60 + off1:03d}.', 0)
                    insert_data['eszkozok_osszesen'] = r.get(f'MERLEG_{61 + off1:03d}.', 0)
                    
                    insert_data['d_sajat_toke'] = r.get(f'MERLEG_{63 + off1:03d}.', 0)
                    insert_data['d_i_jegyzett_toke'] = r.get(f'MERLEG_{64 + off1:03d}.', 0)
                    insert_data['d_i_ebbol_visszavasarolt_tulajdoni_reszesedes'] = r.get(f'MERLEG_{65 + off1:03d}.', 0)
                    insert_data['d_ii_jegyzett_de_meg_be_nem_fizetett_toke'] = r.get(f'MERLEG_{66 + off1:03d}.', 0)
                    insert_data['d_iii_toketartalek'] = r.get(f'MERLEG_{67 + off1:03d}.', 0)
                    insert_data['d_iv_eredmenytartalek'] = r.get(f'MERLEG_{68 + off1:03d}.', 0)
                    insert_data['d_v_lekotott_tartalek'] = r.get(f'MERLEG_{69 + off1:03d}.', 0)
                    insert_data['d_vi_ertekelesi_tartalek'] = r.get(f'MERLEG_{70 + off1:03d}.', 0)
                    insert_data['d_vi_1_ertekhelyesbites_ertekelesi_tartaleka'] = r.get(f'MERLEG_{71 + off1:03d}.', 0)
                    insert_data['d_vi_2_valos_ertekeles_ertekelesi_tartaleka'] = r.get(f'MERLEG_{72 + off1:03d}.', 0)
                    insert_data['d_vii_adozott_eredmeny'] = r.get(f'MERLEG_{73 + off1:03d}.', 0)
                    insert_data['e_celtartalekok'] = r.get(f'MERLEG_{74 + off1:03d}.', 0)
                    insert_data['e_1_celtartalek_a_varhato_kotelezettsegekre'] = r.get(f'MERLEG_{75 + off1:03d}.', 0)
                    insert_data['e_2_celtartalek_a_jovobeni_koltsegekre'] = r.get(f'MERLEG_{76 + off1:03d}.', 0)
                    insert_data['e_3_egyeb_celtartalek'] = r.get(f'MERLEG_{77 + off1:03d}.', 0)
                    insert_data['f_kotelezettsegek'] = r.get(f'MERLEG_{78 + off1:03d}.', 0)
                    insert_data['f_i_hatrasorolt_kotelezettsegek'] = r.get(f'MERLEG_{79 + off1:03d}.', 0)
                    insert_data['f_i_1_hatrasorolt_kotelezettsegek_kapcsolt_vinnel'] = r.get(f'MERLEG_{80 + off1:03d}.', 0)
                    insert_data['f_i_2_hatrasorolt_kotelezettsegek_jelentos_tul_viszonyban'] = r.get(f'MERLEG_{81 + off1:03d}.', 0)
                    insert_data['f_i_3_hatrasorolt_kotelezettsegek_egyeb_reszesedesi_viszonyban'] = r.get(f'MERLEG_{82 + off1:03d}.', 0)
                    insert_data['f_i_4_hatrasorolt_kotelezettsegek_egyeb_gazdalkodoval'] = r.get(f'MERLEG_{83 + off1:03d}.', 0)
                    insert_data['f_ii_hosszu_lejaratu_kotelezettsegek'] = r.get(f'MERLEG_{84 + off1:03d}.', 0)
                    insert_data['f_ii_1_hosszu_lejaratra_kapott_kolcsonok'] = r.get(f'MERLEG_{85 + off1:03d}.', 0)
                    insert_data['f_ii_2_atvaltoztathato_es_atvaltozo_kotvenyek'] = r.get(f'MERLEG_{86 + off1:03d}.', 0)
                    insert_data['f_ii_3_tartozasok_kotvenykibocsatasbol'] = r.get(f'MERLEG_{87 + off1:03d}.', 0)
                    insert_data['f_ii_4_beruhazasi_es_fejlesztesi_hitelek'] = r.get(f'MERLEG_{88 + off1:03d}.', 0)
                    insert_data['f_ii_5_egyeb_hosszu_lejaratu_hitelek'] = r.get(f'MERLEG_{89 + off1:03d}.', 0)
                    insert_data['f_ii_6_tartos_kotelezettsegek_kapcsolt_vinnel'] = r.get(f'MERLEG_{90 + off1:03d}.', 0)
                    insert_data['f_ii_7_tartos_kotelezettsegek_jelentos_tul_viszonyban'] = r.get(f'MERLEG_{91 + off1:03d}.', 0)
                    insert_data['f_ii_8_tartos_kotelezettsegek_egyeb_reszesedesi_viszonyban'] = r.get(f'MERLEG_{92 + off1:03d}.', 0)
                    insert_data['f_ii_9_egyeb_hosszu_lejaratu_kotelezettsegek'] = r.get(f'MERLEG_{93 + off1:03d}.', 0)
                    
                    insert_data['f_ii_10_halasztott_adokotelezettseg'] = r.get('MERLEG_095.', 0) if ev >= 2023 else 0
                    
                    insert_data['f_iii_rovid_lejaratu_kotelezettsegek'] = r.get(f'MERLEG_{94 + off2:03d}.', 0)
                    insert_data['f_iii_1_rovid_lejaratu_kolcsonok'] = r.get(f'MERLEG_{95 + off2:03d}.', 0)
                    insert_data['f_iii_1_ebbol_az_atvaltoztathato_kotvenyek'] = r.get(f'MERLEG_{96 + off2:03d}.', 0)
                    insert_data['f_iii_2_rovid_lejaratu_hitelek'] = r.get(f'MERLEG_{97 + off2:03d}.', 0)
                    insert_data['f_iii_3_vevoktol_kapott_elolegek'] = r.get(f'MERLEG_{98 + off2:03d}.', 0)
                    insert_data['f_iii_4_kotelezettsegek_aruszallitasbol_szolgal_szallitok'] = r.get(f'MERLEG_{99 + off2:03d}.', 0)
                    insert_data['f_iii_5_valtotartozasok'] = r.get(f'MERLEG_{100 + off2:03d}.', 0)
                    insert_data['f_iii_6_rovid_lejaratu_kotelezettsegek_kapcsolt_vinnel'] = r.get(f'MERLEG_{101 + off2:03d}.', 0)
                    insert_data['f_iii_7_rovid_lejaratu_kotelezettsegek_jelentos_tul_viszonyban'] = r.get(f'MERLEG_{102 + off2:03d}.', 0)
                    insert_data['f_iii_8_rovid_lejaratu_kotelezettsegek_egyeb_reszesedesi'] = r.get(f'MERLEG_{103 + off2:03d}.', 0)
                    insert_data['f_iii_9_egyeb_rovid_lejaratu_kotelezettsegek'] = r.get(f'MERLEG_{104 + off2:03d}.', 0)
                    insert_data['f_iii_10_kotelezettsegek_ertekelesi_kulonbozete'] = r.get(f'MERLEG_{105 + off2:03d}.', 0)
                    insert_data['f_iii_11_szarmazekos_ugyletek_negativ_ertekelesi_kulonbozete'] = r.get(f'MERLEG_{106 + off2:03d}.', 0)
                    insert_data['g_passziv_idobeli_elhatarolasok'] = r.get(f'MERLEG_{107 + off2:03d}.', 0)
                    insert_data['g_1_bevetelek_passziv_idobeli_elhatarolasa'] = r.get(f'MERLEG_{108 + off2:03d}.', 0)
                    insert_data['g_2_koltsgek_raforditasok_passziv_idobeli_elhatarolasa'] = r.get(f'MERLEG_{109 + off2:03d}.', 0)
                    insert_data['g_3_halasztott_bevetelek'] = r.get(f'MERLEG_{110 + off2:03d}.', 0)
                    insert_data['forrasok_osszesen'] = r.get(f'MERLEG_{111 + off2:03d}.', 0)

                    insert_data['ek_01_belfoldi_ertekesites_netto_arbevetele'] = r.get('EREDMENYKIMUTATAS_001.', 0)
                    insert_data['ek_02_exportertekesites_netto_arbevetele'] = r.get('EREDMENYKIMUTATAS_002.', 0)
                    insert_data['ek_i_ertekesites_netto_arbevetele'] = r.get('EREDMENYKIMUTATAS_003.', 0)
                    insert_data['ek_03_sajat_termelesu_keszletek_allomanyvaltozasa'] = r.get('EREDMENYKIMUTATAS_004.', 0)
                    insert_data['ek_04_sajat_elallitasi_eszkozok_aktivalt_erteke'] = r.get('EREDMENYKIMUTATAS_005.', 0)
                    insert_data['ek_ii_aktivalt_sajat_teljesitmenyek_erteke'] = r.get('EREDMENYKIMUTATAS_006.', 0)
                    insert_data['ek_iii_egyeb_bevetelek'] = r.get('EREDMENYKIMUTATAS_007.', 0)
                    insert_data['ek_iii_ebbol_visszairt_ertekvesztes'] = r.get('EREDMENYKIMUTATAS_008.', 0)
                    insert_data['ek_05_anyagkoltseg'] = r.get('EREDMENYKIMUTATAS_009.', 0)
                    insert_data['ek_06_igenybe_vett_szolgaltatasok_erteke'] = r.get('EREDMENYKIMUTATAS_010.', 0)
                    insert_data['ek_07_egyeb_szolgaltatasok_erteke'] = r.get('EREDMENYKIMUTATAS_011.', 0)
                    insert_data['ek_08_eladott_aruk_beszerzesi_erteke'] = r.get('EREDMENYKIMUTATAS_012.', 0)
                    insert_data['ek_09_eladott_kozvetitett_szolgaltatasok_erteke'] = r.get('EREDMENYKIMUTATAS_013.', 0)
                    insert_data['ek_iv_anyagjellegu_raforditasok'] = r.get('EREDMENYKIMUTATAS_014.', 0)
                    insert_data['ek_10_berkoltseg'] = r.get('EREDMENYKIMUTATAS_015.', 0)
                    insert_data['ek_11_szemelyi_jellegu_egyeb_kifizetesek'] = r.get('EREDMENYKIMUTATAS_016.', 0)
                    insert_data['ek_12_berjarulekok'] = r.get('EREDMENYKIMUTATAS_017.', 0)
                    insert_data['ek_v_szemelyi_jellegu_raforditasok'] = r.get('EREDMENYKIMUTATAS_018.', 0)
                    insert_data['ek_vi_ertekcsokkenesi_leiras'] = r.get('EREDMENYKIMUTATAS_019.', 0)
                    insert_data['ek_vii_egyeb_raforditasok'] = r.get('EREDMENYKIMUTATAS_020.', 0)
                    insert_data['ek_vii_ebbol_ertekvesztes'] = r.get('EREDMENYKIMUTATAS_021.', 0)
                    insert_data['ek_a_uzemi_uzleti_tevekenyseg_eredmenye'] = r.get('EREDMENYKIMUTATAS_022.', 0)
                    insert_data['ek_13_kapott_jaro_osztalek_es_reszesedes'] = r.get('EREDMENYKIMUTATAS_023.', 0)
                    insert_data['ek_13_ebbol_kapcsolt_viallatkozastol_kapott'] = r.get('EREDMENYKIMUTATAS_024.', 0)
                    insert_data['ek_14_reszesedesekbol_szarmazo_bevetelek_arfolyamnyeresek'] = r.get('EREDMENYKIMUTATAS_025.', 0)
                    insert_data['ek_14_ebbol_kapcsolt_viallatkozastol_kapott'] = r.get('EREDMENYKIMUTATAS_026.', 0)
                    insert_data['ek_15_befektetett_penzugyi_eszkozokbol_szarmazo_bevetelek'] = r.get('EREDMENYKIMUTATAS_027.', 0)
                    insert_data['ek_15_ebbol_kapcsolt_viallatkozastol_kapott'] = r.get('EREDMENYKIMUTATAS_028.', 0)
                    insert_data['ek_16_egyeb_kapott_jaro_kamatok_es_kamatjellegu_bevetelek'] = r.get('EREDMENYKIMUTATAS_029.', 0)
                    insert_data['ek_16_ebbol_kapcsolt_viallatkozastol_kapott'] = r.get('EREDMENYKIMUTATAS_030.', 0)
                    insert_data['ek_17_penzugyi_muveletek_egyeb_bevetelek'] = r.get('EREDMENYKIMUTATAS_031.', 0)
                    insert_data['ek_17_ebbol_ertekelesi_kulonbozet'] = r.get('EREDMENYKIMUTATAS_032.', 0)
                    insert_data['ek_viii_penzugyi_muveletek_bevetelek'] = r.get('EREDMENYKIMUTATAS_033.', 0)
                    insert_data['ek_18_reszesedesekbol_szarmazo_raforditasok_arfolyamveszteségek'] = r.get('EREDMENYKIMUTATAS_034.', 0)
                    insert_data['ek_18_ebbol_kapcsolt_vallalkozasnak_adott'] = r.get('EREDMENYKIMUTATAS_035.', 0)
                    insert_data['ek_19_befektetett_penzugyi_eszkozok_raforditasai'] = r.get('EREDMENYKIMUTATAS_036.', 0)
                    insert_data['ek_19_ebbol_kapcsolt_vallalkozasnak_adott'] = r.get('EREDMENYKIMUTATAS_037.', 0)
                    insert_data['ek_20_fizetendo_kamatok_es_kamatjellegu_raforditasok'] = r.get('EREDMENYKIMUTATAS_038.', 0)
                    insert_data['ek_20_ebbol_kapcsolt_vallalkozasnak_adott'] = r.get('EREDMENYKIMUTATAS_039.', 0)
                    insert_data['ek_21_reszesedesek_ertekpapirok_bankbetetek_ertekvesztese'] = r.get('EREDMENYKIMUTATAS_040.', 0)
                    insert_data['ek_22_penzugyi_muveletek_egyeb_raforditasai'] = r.get('EREDMENYKIMUTATAS_041.', 0)
                    insert_data['ek_22_ebbol_ertekelesi_kulonbozet'] = r.get('EREDMENYKIMUTATAS_042.', 0)
                    insert_data['ek_ix_penzugyi_muveletek_raforditasai'] = r.get('EREDMENYKIMUTATAS_043.', 0)
                    insert_data['ek_b_penzugyi_muveletek_eredmenye'] = r.get('EREDMENYKIMUTATAS_044.', 0)
                    insert_data['ek_c_adozas_elotti_eredmeny'] = r.get('EREDMENYKIMUTATAS_045.', 0)
                    insert_data['ek_x_adofizetesi_kotelezettseg'] = r.get('EREDMENYKIMUTATAS_046.', 0)
                    insert_data['ek_x_1_halasztott_adokulonbozet'] = r.get('EREDMENYKIMUTATAS_047.', 0) if ev >= 2023 else 0
                    insert_data['ek_d_adozott_eredmeny'] = r.get(f'EREDMENYKIMUTATAS_{47 + off3:03d}.', 0)

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
        print("Minden cég és beszámoló adatai sikeresen feltöltve az összes oszloppal!")

    except Exception as e:
        connection.rollback()
        import traceback
        traceback.print_exc()
        print("Hiba történt a folyamat során:", e)
    finally:
        connection.close()

if __name__ == '__main__':
    main()