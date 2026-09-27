SELECT
    BESZAMOLOK.et_ev,
    
    -- =========================================================
    -- ELLENŐRZŐ SZÁMÍTÁSOK (KÜLÖNBSÉGEK)
    -- Ha az adat jó, ezeknek az oszlopoknak 0.00-t kell mutatniuk.
    -- =========================================================
    
    -- Fő egyezőség: Eszközök = Források
    (ADATOK.eszkozok_osszesen - ADATOK.forrasok_osszesen) AS eszkozok_forrasok_DIFF,
    
    -- ESZKÖZÖK BONTÁSA
    (ADATOK.eszkozok_osszesen - (
        ADATOK.a_befektetett_eszkozok +
        ADATOK.b_forgoeszkozok +
        ADATOK.c_aktiv_idobeli_elhatarolasok
    )) AS eszkozok_DIFF,
    
    (ADATOK.a_befektetett_eszkozok - (
        ADATOK.a_i_immaterialis_javak +
        ADATOK.a_ii_targyi_eszkozok +
        ADATOK.a_iii_befektetett_penzugyi_eszkozok +
        ADATOK.a_iv_halasztott_adokoveteles
    )) AS befektetett_eszkozok_DIFF,
    
    (ADATOK.a_i_immaterialis_javak - (
        ADATOK.a_i_1_alapitas_atszervezes_aktivalt_erteke +
        ADATOK.a_i_2_kiserleti_fejlesztes_aktivalt_erteke +
        ADATOK.a_i_3_vagyoni_erteku_jogok +
        ADATOK.a_i_4_szellemi_termekek +
        ADATOK.a_i_5_uzleti_vagy_cegertek +
        ADATOK.a_i_6_immaterialis_javakra_adott_elolegek +
        ADATOK.a_i_7_immaterialis_javak_ertekhelyesbitese
    )) AS immaterialis_javak_DIFF,
    
    (ADATOK.a_ii_targyi_eszkozok - (
        ADATOK.a_ii_1_ingatlanok_es_a_kapcsolodo_vagyoni_erteku_jogok +
        ADATOK.a_ii_2_muszaki_berendezesek_gepek_jarmuvek +
        ADATOK.a_ii_3_egyeb_berendezesek_felszerelesek_jarmuvek +
        ADATOK.a_ii_4_tenyeszallatok +
        ADATOK.a_ii_5_beruhazasok_felujitasok +
        ADATOK.a_ii_6_beruhazasokra_adott_elolegek +
        ADATOK.a_ii_7_targyi_eszkozok_ertekhelyesbitese
    )) AS targyi_eszkozok_DIFF,
    
    (ADATOK.a_iii_befektetett_penzugyi_eszkozok - (
        ADATOK.a_iii_1_tartos_reszesedes_kapcsolt_vallalkozasban +
        ADATOK.a_iii_2_tartosan_adott_kolcson_kapcsolt_vallalkozasban +
        ADATOK.a_iii_3_tartos_jelentos_tulajdoni_reszesedes +
        ADATOK.a_iii_4_tartosan_adott_kolcson_jelentos_tul_viszonyban +
        ADATOK.a_iii_5_egyeb_tartos_reszesedes +
        ADATOK.a_iii_6_tartosan_adott_kolcson_egyeb_reszesedesi_viszonyban +
        ADATOK.a_iii_7_egyeb_tartosan_adott_kolcson +
        ADATOK.a_iii_8_tartos_hitelviszonyt_megtestesito_ertekpapir +
        ADATOK.a_iii_9_befektetett_penzugyi_eszkozok_ertekhelyesbitese +
        ADATOK.a_iii_10_befektetett_penzugyi_eszkozok_ertekelesi_kulonbozete
    )) AS befektetett_penzugyi_eszkozok_DIFF,

    (ADATOK.b_forgoeszkozok - (
        ADATOK.b_i_keszletek +
        ADATOK.b_ii_kovetelesek +
        ADATOK.b_iii_ertekpapirok +
        ADATOK.b_iv_penzeszkozok
    )) AS forgoeszkozok_DIFF,

    (ADATOK.b_i_keszletek - (
        ADATOK.b_i_1_anyagok +
        ADATOK.b_i_2_befejezetlen_termeles_es_felkesz_termekek +
        ADATOK.b_i_3_novendek_hizo_es_egyeb_allatok +
        ADATOK.b_i_4_kesztermekek +
        ADATOK.b_i_5_aruk +
        ADATOK.b_i_6_keszletekre_adott_elolegek
    )) AS keszletek_DIFF,

    (ADATOK.b_ii_kovetelesek - (
        ADATOK.b_ii_1_kovetelesek_aruszallitasbol_szolgaltatasbol_vevok +
        ADATOK.b_ii_2_kovetelesek_kapcsolt_vallalkozassal_szemben +
        ADATOK.b_ii_3_kovetelesek_jelentos_tulajdoni_reszesedesi_viszonyban +
        ADATOK.b_ii_4_kovetelesek_egyeb_reszesedesi_viszonyban +
        ADATOK.b_ii_5_valtokovetelesek +
        ADATOK.b_ii_6_egyeb_kovetelesek +
        ADATOK.b_ii_7_kovetelesek_ertekelesi_kulonbozete +
        ADATOK.b_ii_8_szarmazekos_ugyletek_pozitiv_ertekelesi_kulonbozete
    )) AS kovetelesek_DIFF,

    (ADATOK.b_iii_ertekpapirok - (
        ADATOK.b_iii_1_reszesedes_kapcsolt_vallalkozasban +
        ADATOK.b_iii_2_jelentos_tulajdoni_reszesedes +
        ADATOK.b_iii_3_egyeb_reszesedes +
        ADATOK.b_iii_4_sajat_reszvenyek_sajat_uzletreszek +
        ADATOK.b_iii_5_forgatasi_celu_hitelviszonyt_megtestesito_ertekpapirok +
        ADATOK.b_iii_6_ertekpapirok_ertekelesi_kulonbozete
    )) AS ertekpapirok_DIFF,

    (ADATOK.b_iv_penzeszkozok - (
        ADATOK.b_iv_1_penztar_csekkek +
        ADATOK.b_iv_2_bankbetetek
    )) AS penzeszkozok_DIFF,

    (ADATOK.c_aktiv_idobeli_elhatarolasok - (
        ADATOK.c_1_bevetelek_aktiv_idobeli_elhatarolasa +
        ADATOK.c_2_koltsgek_forditasok_aktiv_idobeli_elhatarolasa +
        ADATOK.c_3_halasztott_raforditasok
    )) AS aktiv_idobeli_elhatarolasok_DIFF,

    -- FORRÁSOK BONTÁSA
    (ADATOK.forrasok_osszesen - (
        ADATOK.d_sajat_toke +
        ADATOK.e_celtartalekok +
        ADATOK.f_kotelezettsegek +
        ADATOK.g_passziv_idobeli_elhatarolasok
    )) AS forrasok_DIFF,

    (ADATOK.d_sajat_toke - (
        ADATOK.d_i_jegyzett_toke +
        ADATOK.d_ii_jegyzett_de_meg_be_nem_fizetett_toke +
        ADATOK.d_iii_toketartalek +
        ADATOK.d_iv_eredmenytartalek +
        ADATOK.d_v_lekotott_tartalek +
        ADATOK.d_vi_ertekelesi_tartalek +
        ADATOK.d_vii_adozott_eredmeny
    )) AS sajat_toke_DIFF,

    (ADATOK.e_celtartalekok - (
        ADATOK.e_1_celtartalek_a_varhato_kotelezettsegekre +
        ADATOK.e_2_celtartalek_a_jovobeni_koltsegekre +
        ADATOK.e_3_egyeb_celtartalek
    )) AS celtartalekok_DIFF,

    (ADATOK.f_kotelezettsegek - (
        ADATOK.f_i_hatrasorolt_kotelezettsegek +
        ADATOK.f_ii_hosszu_lejaratu_kotelezettsegek +
        ADATOK.f_iii_rovid_lejaratu_kotelezettsegek
    )) AS kotelezettsegek_DIFF,

    (ADATOK.f_i_hatrasorolt_kotelezettsegek - (
        ADATOK.f_i_1_hatrasorolt_kotelezettsegek_kapcsolt_vinnel +
        ADATOK.f_i_2_hatrasorolt_kotelezettsegek_jelentos_tul_viszonyban +
        ADATOK.f_i_3_hatrasorolt_kotelezettsegek_egyeb_reszesedesi_viszonyban +
        ADATOK.f_i_4_hatrasorolt_kotelezettsegek_egyeb_gazdalkodoval
    )) AS hatrasorolt_kotelezettsegek_DIFF,

    (ADATOK.f_ii_hosszu_lejaratu_kotelezettsegek - (
        ADATOK.f_ii_1_hosszu_lejaratra_kapott_kolcsonok +
        ADATOK.f_ii_2_atvaltoztathato_es_atvaltozo_kotvenyek +
        ADATOK.f_ii_3_tartozasok_kotvenykibocsatasbol +
        ADATOK.f_ii_4_beruhazasi_es_fejlesztesi_hitelek +
        ADATOK.f_ii_5_egyeb_hosszu_lejaratu_hitelek +
        ADATOK.f_ii_6_tartos_kotelezettsegek_kapcsolt_vinnel +
        ADATOK.f_ii_7_tartos_kotelezettsegek_jelentos_tul_viszonyban +
        ADATOK.f_ii_8_tartos_kotelezettsegek_egyeb_reszesedesi_viszonyban +
        ADATOK.f_ii_9_egyeb_hosszu_lejaratu_kotelezettsegek +
        ADATOK.f_ii_10_halasztott_adokotelezettseg
    )) AS hosszu_lejaratu_kotelezettsegek_DIFF,

    (ADATOK.f_iii_rovid_lejaratu_kotelezettsegek - (
        ADATOK.f_iii_1_rovid_lejaratu_kolcsonok +
        ADATOK.f_iii_2_rovid_lejaratu_hitelek +
        ADATOK.f_iii_3_vevoktol_kapott_elolegek +
        ADATOK.f_iii_4_kotelezettsegek_aruszallitasbol_szolgal_szallitok +
        ADATOK.f_iii_5_valtotartozasok +
        ADATOK.f_iii_6_rovid_lejaratu_kotelezettsegek_kapcsolt_vinnel +
        ADATOK.f_iii_7_rovid_lejaratu_kotelezettsegek_jelentos_tul_viszonyban +
        ADATOK.f_iii_8_rovid_lejaratu_kotelezettsegek_egyeb_reszesedesi +
        ADATOK.f_iii_9_egyeb_rovid_lejaratu_kotelezettsegek +
        ADATOK.f_iii_10_kotelezettsegek_ertekelesi_kulonbozete +
        ADATOK.f_iii_11_szarmazekos_ugyletek_negativ_ertekelesi_kulonbozete
    )) AS rovid_lejaratu_kotelezettsegek_DIFF,

    (ADATOK.g_passziv_idobeli_elhatarolasok - (
        ADATOK.g_1_bevetelek_passziv_idobeli_elhatarolasa +
        ADATOK.g_2_koltsgek_raforditasok_passziv_idobeli_elhatarolasa +
        ADATOK.g_3_halasztott_bevetelek
    )) AS passziv_idobeli_elhatarolasok_DIFF,

    -- EREDMÉNYKIMUTATÁS BONTÁSA
    (ADATOK.ek_i_ertekesites_netto_arbevetele - (
        ADATOK.ek_01_belfoldi_ertekesites_netto_arbevetele +
        ADATOK.ek_02_exportertekesites_netto_arbevetele
    )) AS ek_ertekesites_netto_arbevetele_DIFF,

    (ADATOK.ek_ii_aktivalt_sajat_teljesitmenyek_erteke - (
        ADATOK.ek_03_sajat_termelesu_keszletek_allomanyvaltozasa +
        ADATOK.ek_04_sajat_elallitasi_eszkozok_aktivalt_erteke
    )) AS ek_aktivalt_sajat_teljesitmenyek_DIFF,

    (ADATOK.ek_iv_anyagjellegu_raforditasok - (
        ADATOK.ek_05_anyagkoltseg +
        ADATOK.ek_06_igenybe_vett_szolgaltatasok_erteke +
        ADATOK.ek_07_egyeb_szolgaltatasok_erteke +
        ADATOK.ek_08_eladott_aruk_beszerzesi_erteke +
        ADATOK.ek_09_eladott_kozvetitett_szolgaltatasok_erteke
    )) AS ek_anyagjellegu_raforditasok_DIFF,

    (ADATOK.ek_v_szemelyi_jellegu_raforditasok - (
        ADATOK.ek_10_berkoltseg +
        ADATOK.ek_11_szemelyi_jellegu_egyeb_kifizetesek +
        ADATOK.ek_12_berjarulekok
    )) AS ek_szemelyi_jellegu_raforditasok_DIFF,


    -- =========================================================
    -- NYERS ADATOK FELSOROLÁSA
    -- =========================================================
    ADATOK.eszkozok_osszesen,
        ADATOK.a_befektetett_eszkozok,
            ADATOK.a_i_immaterialis_javak,
                ADATOK.a_i_1_alapitas_atszervezes_aktivalt_erteke,
                ADATOK.a_i_2_kiserleti_fejlesztes_aktivalt_erteke,
                ADATOK.a_i_3_vagyoni_erteku_jogok,
                ADATOK.a_i_4_szellemi_termekek,
                ADATOK.a_i_5_uzleti_vagy_cegertek,
                ADATOK.a_i_6_immaterialis_javakra_adott_elolegek,
                ADATOK.a_i_7_immaterialis_javak_ertekhelyesbitese,
            ADATOK.a_ii_targyi_eszkozok,
                ADATOK.a_ii_1_ingatlanok_es_a_kapcsolodo_vagyoni_erteku_jogok,
                ADATOK.a_ii_2_muszaki_berendezesek_gepek_jarmuvek,
                ADATOK.a_ii_3_egyeb_berendezesek_felszerelesek_jarmuvek,
                ADATOK.a_ii_4_tenyeszallatok,
                ADATOK.a_ii_5_beruhazasok_felujitasok,
                ADATOK.a_ii_6_beruhazasokra_adott_elolegek,
                ADATOK.a_ii_7_targyi_eszkozok_ertekhelyesbitese,
            ADATOK.a_iii_befektetett_penzugyi_eszkozok,
                ADATOK.a_iii_1_tartos_reszesedes_kapcsolt_vallalkozasban,
                ADATOK.a_iii_2_tartosan_adott_kolcson_kapcsolt_vallalkozasban,
                ADATOK.a_iii_3_tartos_jelentos_tulajdoni_reszesedes,
                ADATOK.a_iii_4_tartosan_adott_kolcson_jelentos_tul_viszonyban,
                ADATOK.a_iii_5_egyeb_tartos_reszesedes,
                ADATOK.a_iii_6_tartosan_adott_kolcson_egyeb_reszesedesi_viszonyban,
                ADATOK.a_iii_7_egyeb_tartosan_adott_kolcson,
                ADATOK.a_iii_8_tartos_hitelviszonyt_megtestesito_ertekpapir,
                ADATOK.a_iii_9_befektetett_penzugyi_eszkozok_ertekhelyesbitese,
                ADATOK.a_iii_10_befektetett_penzugyi_eszkozok_ertekelesi_kulonbozete,
            ADATOK.a_iv_halasztott_adokoveteles,
        ADATOK.b_forgoeszkozok,
            ADATOK.b_i_keszletek,
                ADATOK.b_i_1_anyagok,
                ADATOK.b_i_2_befejezetlen_termeles_es_felkesz_termekek,
                ADATOK.b_i_3_novendek_hizo_es_egyeb_allatok,
                ADATOK.b_i_4_kesztermekek,
                ADATOK.b_i_5_aruk,
                ADATOK.b_i_6_keszletekre_adott_elolegek,
            ADATOK.b_ii_kovetelesek,
                ADATOK.b_ii_1_kovetelesek_aruszallitasbol_szolgaltatasbol_vevok,
                ADATOK.b_ii_2_kovetelesek_kapcsolt_vallalkozassal_szemben,
                ADATOK.b_ii_3_kovetelesek_jelentos_tulajdoni_reszesedesi_viszonyban,
                ADATOK.b_ii_4_kovetelesek_egyeb_reszesedesi_viszonyban,
                ADATOK.b_ii_5_valtokovetelesek,
                ADATOK.b_ii_6_egyeb_kovetelesek,
                ADATOK.b_ii_7_kovetelesek_ertekelesi_kulonbozete,
                ADATOK.b_ii_8_szarmazekos_ugyletek_pozitiv_ertekelesi_kulonbozete,
            ADATOK.b_iii_ertekpapirok,
                ADATOK.b_iii_1_reszesedes_kapcsolt_vallalkozasban,
                ADATOK.b_iii_2_jelentos_tulajdoni_reszesedes,
                ADATOK.b_iii_3_egyeb_reszesedes,
                ADATOK.b_iii_4_sajat_reszvenyek_sajat_uzletreszek,
                ADATOK.b_iii_5_forgatasi_celu_hitelviszonyt_megtestesito_ertekpapirok,
                ADATOK.b_iii_6_ertekpapirok_ertekelesi_kulonbozete,
            ADATOK.b_iv_penzeszkozok,
                ADATOK.b_iv_1_penztar_csekkek,
                ADATOK.b_iv_2_bankbetetek,
        ADATOK.c_aktiv_idobeli_elhatarolasok,
            ADATOK.c_1_bevetelek_aktiv_idobeli_elhatarolasa,
            ADATOK.c_2_koltsgek_forditasok_aktiv_idobeli_elhatarolasa,
            ADATOK.c_3_halasztott_raforditasok,

    ADATOK.forrasok_osszesen,
        ADATOK.d_sajat_toke,
            ADATOK.d_i_jegyzett_toke,
                ADATOK.d_i_ebbol_visszavasarolt_tulajdoni_reszesedes,
            ADATOK.d_ii_jegyzett_de_meg_be_nem_fizetett_toke,
            ADATOK.d_iii_toketartalek,
            ADATOK.d_iv_eredmenytartalek,
            ADATOK.d_v_lekotott_tartalek,
            ADATOK.d_vi_ertekelesi_tartalek,
                ADATOK.d_vi_1_ertekhelyesbites_ertekelesi_tartaleka,
                ADATOK.d_vi_2_valos_ertekeles_ertekelesi_tartaleka,
            ADATOK.d_vii_adozott_eredmeny,
        ADATOK.e_celtartalekok,
            ADATOK.e_1_celtartalek_a_varhato_kotelezettsegekre,
            ADATOK.e_2_celtartalek_a_jovobeni_koltsegekre,
            ADATOK.e_3_egyeb_celtartalek,
        ADATOK.f_kotelezettsegek,
            ADATOK.f_i_hatrasorolt_kotelezettsegek,
                ADATOK.f_i_1_hatrasorolt_kotelezettsegek_kapcsolt_vinnel,
                ADATOK.f_i_2_hatrasorolt_kotelezettsegek_jelentos_tul_viszonyban,
                ADATOK.f_i_3_hatrasorolt_kotelezettsegek_egyeb_reszesedesi_viszonyban,
                ADATOK.f_i_4_hatrasorolt_kotelezettsegek_egyeb_gazdalkodoval,
            ADATOK.f_ii_hosszu_lejaratu_kotelezettsegek,
                ADATOK.f_ii_1_hosszu_lejaratra_kapott_kolcsonok,
                ADATOK.f_ii_2_atvaltoztathato_es_atvaltozo_kotvenyek,
                ADATOK.f_ii_3_tartozasok_kotvenykibocsatasbol,
                ADATOK.f_ii_4_beruhazasi_es_fejlesztesi_hitelek,
                ADATOK.f_ii_5_egyeb_hosszu_lejaratu_hitelek,
                ADATOK.f_ii_6_tartos_kotelezettsegek_kapcsolt_vinnel,
                ADATOK.f_ii_7_tartos_kotelezettsegek_jelentos_tul_viszonyban,
                ADATOK.f_ii_8_tartos_kotelezettsegek_egyeb_reszesedesi_viszonyban,
                ADATOK.f_ii_9_egyeb_hosszu_lejaratu_kotelezettsegek,
                ADATOK.f_ii_10_halasztott_adokotelezettseg,
            ADATOK.f_iii_rovid_lejaratu_kotelezettsegek,
                ADATOK.f_iii_1_rovid_lejaratu_kolcsonok,
                    ADATOK.f_iii_1_ebbol_az_atvaltoztathato_kotvenyek,
                ADATOK.f_iii_2_rovid_lejaratu_hitelek,
                ADATOK.f_iii_3_vevoktol_kapott_elolegek,
                ADATOK.f_iii_4_kotelezettsegek_aruszallitasbol_szolgal_szallitok,
                ADATOK.f_iii_5_valtotartozasok,
                ADATOK.f_iii_6_rovid_lejaratu_kotelezettsegek_kapcsolt_vinnel,
                ADATOK.f_iii_7_rovid_lejaratu_kotelezettsegek_jelentos_tul_viszonyban,
                ADATOK.f_iii_8_rovid_lejaratu_kotelezettsegek_egyeb_reszesedesi,
                ADATOK.f_iii_9_egyeb_rovid_lejaratu_kotelezettsegek,
                ADATOK.f_iii_10_kotelezettsegek_ertekelesi_kulonbozete,
                ADATOK.f_iii_11_szarmazekos_ugyletek_negativ_ertekelesi_kulonbozete,
        ADATOK.g_passziv_idobeli_elhatarolasok,
            ADATOK.g_1_bevetelek_passziv_idobeli_elhatarolasa,
            ADATOK.g_2_koltsgek_raforditasok_passziv_idobeli_elhatarolasa,
            ADATOK.g_3_halasztott_bevetelek,

    -- EREDMÉNYKIMUTATÁS NYERS ADATOK
    ADATOK.ek_01_belfoldi_ertekesites_netto_arbevetele,
    ADATOK.ek_02_exportertekesites_netto_arbevetele,
    ADATOK.ek_i_ertekesites_netto_arbevetele,
    ADATOK.ek_03_sajat_termelesu_keszletek_allomanyvaltozasa,
    ADATOK.ek_04_sajat_elallitasi_eszkozok_aktivalt_erteke,
    ADATOK.ek_ii_aktivalt_sajat_teljesitmenyek_erteke,
    ADATOK.ek_iii_egyeb_bevetelek,
        ADATOK.ek_iii_ebbol_visszairt_ertekvesztes,
    ADATOK.ek_05_anyagkoltseg,
    ADATOK.ek_06_igenybe_vett_szolgaltatasok_erteke,
    ADATOK.ek_07_egyeb_szolgaltatasok_erteke,
    ADATOK.ek_08_eladott_aruk_beszerzesi_erteke,
    ADATOK.ek_09_eladott_kozvetitett_szolgaltatasok_erteke,
    ADATOK.ek_iv_anyagjellegu_raforditasok,
    ADATOK.ek_10_berkoltseg,
    ADATOK.ek_11_szemelyi_jellegu_egyeb_kifizetesek,
    ADATOK.ek_12_berjarulekok,
    ADATOK.ek_v_szemelyi_jellegu_raforditasok,
    ADATOK.ek_vi_ertekcsokkenesi_leiras,
    ADATOK.ek_vii_egyeb_raforditasok,
        ADATOK.ek_vii_ebbol_ertekvesztes,
    ADATOK.ek_a_uzemi_uzleti_tevekenyseg_eredmenye,
    ADATOK.ek_13_kapott_jaro_osztalek_es_reszesedes,
        ADATOK.ek_13_ebbol_kapcsolt_viallatkozastol_kapott,
    ADATOK.ek_14_reszesedesekbol_szarmazo_bevetelek_arfolyamnyeresek,
        ADATOK.ek_14_ebbol_kapcsolt_viallatkozastol_kapott,
    ADATOK.ek_15_befektetett_penzugyi_eszkozokbol_szarmazo_bevetelek,
        ADATOK.ek_15_ebbol_kapcsolt_viallatkozastol_kapott,
    ADATOK.ek_16_egyeb_kapott_jaro_kamatok_es_kamatjellegu_bevetelek,
        ADATOK.ek_16_ebbol_kapcsolt_viallatkozastol_kapott,
    ADATOK.ek_17_penzugyi_muveletek_egyeb_bevetelek,
        ADATOK.ek_17_ebbol_ertekelesi_kulonbozet,
    ADATOK.ek_viii_penzugyi_muveletek_bevetelek,
    ADATOK.ek_18_reszesedesekbol_szarmazo_raforditasok_arfolyamveszteségek,
        ADATOK.ek_18_ebbol_kapcsolt_vallalkozasnak_adott,
    ADATOK.ek_19_befektetett_penzugyi_eszkozok_raforditasai,
        ADATOK.ek_19_ebbol_kapcsolt_vallalkozasnak_adott,
    ADATOK.ek_20_fizetendo_kamatok_es_kamatjellegu_raforditasok,
        ADATOK.ek_20_ebbol_kapcsolt_vallalkozasnak_adott,
    ADATOK.ek_21_reszesedesek_ertekpapirok_bankbetetek_ertekvesztese,
    ADATOK.ek_22_penzugyi_muveletek_egyeb_raforditasai,
        ADATOK.ek_22_ebbol_ertekelesi_kulonbozet,
    ADATOK.ek_ix_penzugyi_muveletek_raforditasai,
    ADATOK.ek_b_penzugyi_muveletek_eredmenye,
    ADATOK.ek_c_adozas_elotti_eredmeny,
    ADATOK.ek_x_adofizetesi_kotelezettseg,
    ADATOK.ek_x_1_halasztott_adokulonbozet,
    ADATOK.ek_d_adozott_eredmeny

FROM
    02773_research.beszamolo_adatok ADATOK 
    INNER JOIN 02773_research.beszamolok BESZAMOLOK
        ON ADATOK.beszamolo_id = BESZAMOLOK.id
;