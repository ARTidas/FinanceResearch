import pymysql
import pandas as pd
import numpy as np
import re
from config import DB_CONFIG

def make_safe_filename(name):
    safe_name = re.sub(r'[^\w\s-]', '', name)
    safe_name = re.sub(r'[\s]+', '_', safe_name)
    return safe_name.strip('_')

def main():
    sql_query = """
    SELECT
        CEGEK.nev AS cegnev,
        BESZAMOLOK.et_ev,
        
        (ADATOK.eszkozok_osszesen - ADATOK.forrasok_osszesen) AS eszkozok_forrasok_DIFF,
        (ADATOK.eszkozok_osszesen - (
            ADATOK.a_befektetett_eszkozok + ADATOK.b_forgoeszkozok + ADATOK.c_aktiv_idobeli_elhatarolasok
        )) AS eszkozok_DIFF,
        (ADATOK.a_befektetett_eszkozok - (
            ADATOK.a_i_immaterialis_javak + ADATOK.a_ii_targyi_eszkozok + 
            ADATOK.a_iii_befektetett_penzugyi_eszkozok + IFNULL(ADATOK.a_iv_halasztott_adokoveteles, 0)
        )) AS befektetett_eszkozok_DIFF,
        (ADATOK.a_i_immaterialis_javak - (
            ADATOK.a_i_1_alapitas_atszervezes_aktivalt_erteke + ADATOK.a_i_2_kiserleti_fejlesztes_aktivalt_erteke +
            ADATOK.a_i_3_vagyoni_erteku_jogok + ADATOK.a_i_4_szellemi_termekek +
            ADATOK.a_i_5_uzleti_vagy_cegertek + ADATOK.a_i_6_immaterialis_javakra_adott_elolegek +
            ADATOK.a_i_7_immaterialis_javak_ertekhelyesbitese
        )) AS immaterialis_javak_DIFF,
        (ADATOK.a_ii_targyi_eszkozok - (
            ADATOK.a_ii_1_ingatlanok_es_a_kapcsolodo_vagyoni_erteku_jogok + ADATOK.a_ii_2_muszaki_berendezesek_gepek_jarmuvek +
            ADATOK.a_ii_3_egyeb_berendezesek_felszerelesek_jarmuvek + ADATOK.a_ii_4_tenyeszallatok +
            ADATOK.a_ii_5_beruhazasok_felujitasok + ADATOK.a_ii_6_beruhazasokra_adott_elolegek +
            ADATOK.a_ii_7_targyi_eszkozok_ertekhelyesbitese
        )) AS targyi_eszkozok_DIFF,
        (ADATOK.a_iii_befektetett_penzugyi_eszkozok - (
            ADATOK.a_iii_1_tartos_reszesedes_kapcsolt_vallalkozasban + ADATOK.a_iii_2_tartosan_adott_kolcson_kapcsolt_vallalkozasban +
            ADATOK.a_iii_3_tartos_jelentos_tulajdoni_reszesedes + ADATOK.a_iii_4_tartosan_adott_kolcson_jelentos_tul_viszonyban +
            ADATOK.a_iii_5_egyeb_tartos_reszesedes + ADATOK.a_iii_6_tartosan_adott_kolcson_egyeb_reszesedesi_viszonyban +
            ADATOK.a_iii_7_egyeb_tartosan_adott_kolcson + ADATOK.a_iii_8_tartos_hitelviszonyt_megtestesito_ertekpapir +
            ADATOK.a_iii_9_befektetett_penzugyi_eszkozok_ertekhelyesbitese + ADATOK.a_iii_10_befektetett_penzugyi_eszkozok_ertekelesi_kulonbozete
        )) AS befektetett_penzugyi_eszkozok_DIFF,
        (ADATOK.b_forgoeszkozok - (
            ADATOK.b_i_keszletek + ADATOK.b_ii_kovetelesek + ADATOK.b_iii_ertekpapirok + ADATOK.b_iv_penzeszkozok
        )) AS forgoeszkozok_DIFF,
        (ADATOK.b_i_keszletek - (
            ADATOK.b_i_1_anyagok + ADATOK.b_i_2_befejezetlen_termeles_es_felkesz_termekek +
            ADATOK.b_i_3_novendek_hizo_es_egyeb_allatok + ADATOK.b_i_4_kesztermekek +
            ADATOK.b_i_5_aruk + ADATOK.b_i_6_keszletekre_adott_elolegek
        )) AS keszletek_DIFF,
        (ADATOK.b_ii_kovetelesek - (
            ADATOK.b_ii_1_kovetelesek_aruszallitasbol_szolgaltatasbol_vevok + ADATOK.b_ii_2_kovetelesek_kapcsolt_vallalkozassal_szemben +
            ADATOK.b_ii_3_kovetelesek_jelentos_tulajdoni_reszesedesi_viszonyban + ADATOK.b_ii_4_kovetelesek_egyeb_reszesedesi_viszonyban +
            ADATOK.b_ii_5_valtokovetelesek + ADATOK.b_ii_6_egyeb_kovetelesek +
            ADATOK.b_ii_7_kovetelesek_ertekelesi_kulonbozete + ADATOK.b_ii_8_szarmazekos_ugyletek_pozitiv_ertekelesi_kulonbozete
        )) AS kovetelesek_DIFF,
        (ADATOK.b_iii_ertekpapirok - (
            ADATOK.b_iii_1_reszesedes_kapcsolt_vallalkozasban + ADATOK.b_iii_2_jelentos_tulajdoni_reszesedes +
            ADATOK.b_iii_3_egyeb_reszesedes + ADATOK.b_iii_4_sajat_reszvenyek_sajat_uzletreszek +
            ADATOK.b_iii_5_forgatasi_celu_hitelviszonyt_megtestesito_ertekpapirok + ADATOK.b_iii_6_ertekpapirok_ertekelesi_kulonbozete
        )) AS ertekpapirok_DIFF,
        (ADATOK.b_iv_penzeszkozok - (
            ADATOK.b_iv_1_penztar_csekkek + ADATOK.b_iv_2_bankbetetek
        )) AS penzeszkozok_DIFF,
        (ADATOK.c_aktiv_idobeli_elhatarolasok - (
            ADATOK.c_1_bevetelek_aktiv_idobeli_elhatarolasa + ADATOK.c_2_koltsgek_forditasok_aktiv_idobeli_elhatarolasa + ADATOK.c_3_halasztott_raforditasok
        )) AS aktiv_idobeli_elhatarolasok_DIFF,

        (ADATOK.forrasok_osszesen - (
            ADATOK.d_sajat_toke + ADATOK.e_celtartalekok + ADATOK.f_kotelezettsegek + ADATOK.g_passziv_idobeli_elhatarolasok
        )) AS forrasok_DIFF,
        (ADATOK.d_sajat_toke - (
            ADATOK.d_i_jegyzett_toke + ADATOK.d_ii_jegyzett_de_meg_be_nem_fizetett_toke +
            ADATOK.d_iii_toketartalek + ADATOK.d_iv_eredmenytartalek + ADATOK.d_v_lekotott_tartalek +
            ADATOK.d_vi_ertekelesi_tartalek + ADATOK.d_vii_adozott_eredmeny
        )) AS sajat_toke_DIFF,
        (ADATOK.e_celtartalekok - (
            ADATOK.e_1_celtartalek_a_varhato_kotelezettsegekre + ADATOK.e_2_celtartalek_a_jovobeni_koltsegekre + ADATOK.e_3_egyeb_celtartalek
        )) AS celtartalekok_DIFF,
        (ADATOK.f_kotelezettsegek - (
            ADATOK.f_i_hatrasorolt_kotelezettsegek + ADATOK.f_ii_hosszu_lejaratu_kotelezettsegek + ADATOK.f_iii_rovid_lejaratu_kotelezettsegek
        )) AS kotelezettsegek_DIFF,
        (ADATOK.f_i_hatrasorolt_kotelezettsegek - (
            ADATOK.f_i_1_hatrasorolt_kotelezettsegek_kapcsolt_vinnel + ADATOK.f_i_2_hatrasorolt_kotelezettsegek_jelentos_tul_viszonyban +
            ADATOK.f_i_3_hatrasorolt_kotelezettsegek_egyeb_reszesedesi_viszonyban + ADATOK.f_i_4_hatrasorolt_kotelezettsegek_egyeb_gazdalkodoval
        )) AS hatrasorolt_kotelezettsegek_DIFF,
        (ADATOK.f_ii_hosszu_lejaratu_kotelezettsegek - (
            ADATOK.f_ii_1_hosszu_lejaratra_kapott_kolcsonok + ADATOK.f_ii_2_atvaltoztathato_es_atvaltozo_kotvenyek +
            ADATOK.f_ii_3_tartozasok_kotvenykibocsatasbol + ADATOK.f_ii_4_beruhazasi_es_fejlesztesi_hitelek +
            ADATOK.f_ii_5_egyeb_hosszu_lejaratu_hitelek + ADATOK.f_ii_6_tartos_kotelezettsegek_kapcsolt_vinnel +
            ADATOK.f_ii_7_tartos_kotelezettsegek_jelentos_tul_viszonyban + ADATOK.f_ii_8_tartos_kotelezettsegek_egyeb_reszesedesi_viszonyban +
            ADATOK.f_ii_9_egyeb_hosszu_lejaratu_kotelezettsegek + IFNULL(ADATOK.f_ii_10_halasztott_adokotelezettseg, 0)
        )) AS hosszu_lejaratu_kotelezettsegek_DIFF,
        (ADATOK.f_iii_rovid_lejaratu_kotelezettsegek - (
            ADATOK.f_iii_1_rovid_lejaratu_kolcsonok + ADATOK.f_iii_2_rovid_lejaratu_hitelek +
            ADATOK.f_iii_3_vevoktol_kapott_elolegek + ADATOK.f_iii_4_kotelezettsegek_aruszallitasbol_szolgal_szallitok +
            ADATOK.f_iii_5_valtotartozasok + ADATOK.f_iii_6_rovid_lejaratu_kotelezettsegek_kapcsolt_vinnel +
            ADATOK.f_iii_7_rovid_lejaratu_kotelezettsegek_jelentos_tul_viszonyban + ADATOK.f_iii_8_rovid_lejaratu_kotelezettsegek_egyeb_reszesedesi +
            ADATOK.f_iii_9_egyeb_rovid_lejaratu_kotelezettsegek + ADATOK.f_iii_10_kotelezettsegek_ertekelesi_kulonbozete +
            ADATOK.f_iii_11_szarmazekos_ugyletek_negativ_ertekelesi_kulonbozete
        )) AS rovid_lejaratu_kotelezettsegek_DIFF,
        (ADATOK.g_passziv_idobeli_elhatarolasok - (
            ADATOK.g_1_bevetelek_passziv_idobeli_elhatarolasa + ADATOK.g_2_koltsgek_raforditasok_passziv_idobeli_elhatarolasa + ADATOK.g_3_halasztott_bevetelek
        )) AS passziv_idobeli_elhatarolasok_DIFF,

        (ADATOK.ek_i_ertekesites_netto_arbevetele - (
            ADATOK.ek_01_belfoldi_ertekesites_netto_arbevetele + ADATOK.ek_02_exportertekesites_netto_arbevetele
        )) AS ek_ertekesites_netto_arbevetele_DIFF,
        (ADATOK.ek_ii_aktivalt_sajat_teljesitmenyek_erteke - (
            ADATOK.ek_03_sajat_termelesu_keszletek_allomanyvaltozasa + ADATOK.ek_04_sajat_elallitasi_eszkozok_aktivalt_erteke
        )) AS ek_aktivalt_sajat_teljesitmenyek_DIFF,
        (ADATOK.ek_iv_anyagjellegu_raforditasok - (
            ADATOK.ek_05_anyagkoltseg + ADATOK.ek_06_igenybe_vett_szolgaltatasok_erteke +
            ADATOK.ek_07_egyeb_szolgaltatasok_erteke + ADATOK.ek_08_eladott_aruk_beszerzesi_erteke +
            ADATOK.ek_09_eladott_kozvetitett_szolgaltatasok_erteke
        )) AS ek_anyagjellegu_raforditasok_DIFF,
        (ADATOK.ek_v_szemelyi_jellegu_raforditasok - (
            ADATOK.ek_10_berkoltseg + ADATOK.ek_11_szemelyi_jellegu_egyeb_kifizetesek + ADATOK.ek_12_berjarulekok
        )) AS ek_szemelyi_jellegu_raforditasok_DIFF,
        
        ADATOK.*
        
    FROM
        02773_research.beszamolo_adatok ADATOK 
        INNER JOIN 02773_research.beszamolok BESZAMOLOK ON ADATOK.beszamolo_id = BESZAMOLOK.id
        INNER JOIN 02773_research.cegek CEGEK ON BESZAMOLOK.ceg_id = CEGEK.id
    ORDER BY BESZAMOLOK.et_ev ASC;
    """

    print("🔌 Kapcsolódás az adatbázishoz...")
    connection = pymysql.connect(
        host=DB_CONFIG['host'], port=DB_CONFIG['port'],
        user=DB_CONFIG['user'], password=DB_CONFIG['password'],
        database=DB_CONFIG['database'], charset='utf8mb4'
    )

    try:
        df_all = pd.read_sql(sql_query, connection)
        if df_all.empty:
            print("Nincs feldolgozható adat az adatbázisban.")
            return

        cegek = df_all['cegnev'].unique()
        print(f"\n🏢 Talált cégek száma: {len(cegek)}")

        for cegnev in cegek:
            print(f"\n========================================")
            print(f"📄 Feldolgozás és audit: {cegnev}")
            
            df_ceg = df_all[df_all['cegnev'] == cegnev].copy().sort_values(by='et_ev').reset_index(drop=True)
            diff_columns = [col for col in df_ceg.columns if col.endswith('_DIFF')]
            
            # Beszámolótípusokhoz tartozó szabályok
            main_diffs = {'eszkozok_forrasok_DIFF', 'eszkozok_DIFF', 'forrasok_DIFF'}
            roman_diffs = {'befektetett_eszkozok_DIFF', 'forgoeszkozok_DIFF', 'sajat_toke_DIFF', 'kotelezettsegek_DIFF'}
            
            for index, row in df_ceg.iterrows():
                ev = int(row['et_ev']) if pd.notna(row['et_ev']) else "Ismeretlen"
                hibak = []
                
                # Egyszerűsített és Mikrogazdálkodói struktúrák intelligens azonosítása
                is_simplified = (row['ek_10_berkoltseg'] == 0 and row['a_ii_1_ingatlanok_es_a_kapcsolodo_vagyoni_erteku_jogok'] == 0)
                is_mikro = (is_simplified and row['a_ii_targyi_eszkozok'] == 0 and row['d_i_jegyzett_toke'] == 0)

                for col in diff_columns:
                    if is_mikro and col not in main_diffs:
                        continue # A mikróban csak 7 sor van, a többit nem szabad összegezni
                    if is_simplified and not is_mikro and col not in main_diffs and col not in roman_diffs:
                        continue # Az egyszerűsítettben nincsenek arab számos részletezések
                        
                    if pd.notna(row[col]) and abs(row[col]) > 0.01:
                        hibak.append(f"{col}: Eltérés = {row[col]:.2f}")
                
                if hibak:
                    print(f"❌ {ev}. év: Belső egyezőségi hibák találhatók!")
                    for hiba in hibak:
                        print(f"   - {hiba}")
                else:
                    print(f"✅ {ev}. év: Minden vizsgált főösszeg tökéletesen egyezik a részletekkel.")

            print("📈 Pénzügyi mutatók (KPI) kiszámítása...")
            
            # Vagyon változása (Ha nincs előző év, akkor NaN lesz, ami normális)
            df_ceg['MUTATO: Vagyon változása (%)'] = np.where(
                df_ceg['eszkozok_osszesen'].shift(1) > 0,
                ((df_ceg['eszkozok_osszesen'] / df_ceg['eszkozok_osszesen'].shift(1)) - 1) * 100,
                0
            )
            
            elso_ev_vagyona = df_ceg['eszkozok_osszesen'].iloc[0]
            elso_ev = df_ceg['et_ev'].iloc[0]
            
            df_ceg['MUTATO: Vagyon CAGR a bázisévtől (%)'] = df_ceg.apply(
                lambda row: (((row['eszkozok_osszesen'] / elso_ev_vagyona) ** (1 / (row['et_ev'] - elso_ev))) - 1) * 100 
                if (row['et_ev'] - elso_ev) > 0 and elso_ev_vagyona > 0 else 0, axis=1
            )
            
            df_ceg['MUTATO: Saját tőke aránya (%)'] = np.where(
                df_ceg['forrasok_osszesen'] > 0,
                (df_ceg['d_sajat_toke'] / df_ceg['forrasok_osszesen']) * 100, 0
            )
            
            df_ceg['MUTATO: Eladósodottság / Idegen tőke aránya (%)'] = np.where(
                df_ceg['forrasok_osszesen'] > 0,
                ((df_ceg['f_kotelezettsegek'] + df_ceg['g_passziv_idobeli_elhatarolasok']) / df_ceg['forrasok_osszesen']) * 100, 0
            )
            
            df_ceg['MUTATO: Tőke + Idegen tőke ELLENŐRZÉS (%)'] = df_ceg['MUTATO: Saját tőke aránya (%)'] + df_ceg['MUTATO: Eladósodottság / Idegen tőke aránya (%)']
            
            df_ceg['MUTATO: Tőkefeszültség (%)'] = np.where(
                df_ceg['d_sajat_toke'] != 0,
                ((df_ceg['f_kotelezettsegek'] + df_ceg['g_passziv_idobeli_elhatarolasok']) / df_ceg['d_sajat_toke']) * 100, 0
            )
            
            # Megvédi a kódot attól, ha egy Mikrogazdálkodói beszámolóban nincs 'Jegyzett tőke' (0-val osztás ellen)
            df_ceg['MUTATO: Saját tőke szorzó (jegyzett tőkéhez) (%)'] = np.where(
                df_ceg['d_i_jegyzett_toke'] > 0,
                (df_ceg['d_sajat_toke'] / df_ceg['d_i_jegyzett_toke']) * 100, 0
            )
            
            df_ceg['MUTATO: Saját tőke változása (%)'] = df_ceg['MUTATO: Saját tőke szorzó (jegyzett tőkéhez) (%)'] - df_ceg['MUTATO: Saját tőke szorzó (jegyzett tőkéhez) (%)'].shift(1)
            
            df_ceg['MUTATO: Fedezet I. mutató (%)'] = np.where(
                df_ceg['a_befektetett_eszkozok'] > 0,
                (df_ceg['d_sajat_toke'] / df_ceg['a_befektetett_eszkozok']) * 100, 0
            )
            
            df_ceg['MUTATO: Fedezet II. mutató (%)'] = np.where(
                df_ceg['a_befektetett_eszkozok'] > 0,
                ((df_ceg['d_sajat_toke'] + df_ceg['f_ii_hosszu_lejaratu_kotelezettsegek']) / df_ceg['a_befektetett_eszkozok']) * 100, 0
            )

            # Exportálás
            safe_cegnev = make_safe_filename(cegnev)
            excel_filename = f"{safe_cegnev}_Beszamolo_Elemzes.xlsx"
            
            df_ceg = df_ceg.drop(columns=['cegnev'])
            df_ceg['et_ev'] = df_ceg['et_ev'].fillna(0).astype(int)
            
            df_transposed = df_ceg.set_index('et_ev').T
            df_transposed.index.name = 'Attribútum / Mutató'
            df_transposed.columns.name = 'Év'
            
            df_transposed.to_excel(excel_filename, index=True)
            print(f"💾 Fájl sikeresen legenerálva: {excel_filename}")

    except Exception as e:
        import traceback
        print("Hiba történt a lekérdezés vagy feldolgozás során:")
        traceback.print_exc()
    finally:
        connection.close()
        print("\nKapcsolat lezárva. Elemzések befejezve.")

if __name__ == "__main__":
    main()