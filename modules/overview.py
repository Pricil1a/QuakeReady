"""Halaman Overview; isi dan interaksi mengikuti proyek acuan QuakeReady."""
from __future__ import annotations

def render(context):
    """Render halaman menggunakan dataset dan helper dari app.py."""
    globals().update(context)
    st.markdown('''<div class="qr-hero"><div class="qr-hero-tag"><span class="line"></span>INDONESIAN SEISMIC RESEARCH · 1998—2024</div><h1>Indonesia, dipahami melalui data seismik.</h1><p>Observatorium interaktif untuk mempelajari distribusi kejadian, membaca pola spasio-temporal, dan mengeksplorasi hasil penelitian Hybrid ST-GNN.</p><div class="qr-hero-meta">27 tahun pengamatan &nbsp; / &nbsp; Katalog BMKG &nbsp; / &nbsp; Analisis berbasis grid</div></div>''',unsafe_allow_html=True)
    has_catalogue=E is not None
    has_history=H is not None
    if not has_catalogue:
        st.markdown('<div class="qr-inline-context"><strong>MODE PRATINJAU PENELITIAN</strong> · Angka dan grafik awal diambil dari output notebook, bukan dari CSV yang sedang terhubung. Hubungkan katalog agar seluruh filter, tabel kejadian, dan statistik lengkap aktif.</div>',unsafe_allow_html=True)
    cols=st.columns(4,gap='small')
    vals=[('KEJADIAN HISTORIS',number(len(E)) if has_catalogue else number(NOTEBOOK_COUNTS['events']),
           'Katalog terhubung' if has_catalogue else 'Rangkuman output notebook'),
          ('GRID PENELITIAN',number(len(H)) if has_history else number(NOTEBOOK_COUNTS['grids']),
           'File historis aktif' if has_history else 'Jumlah grid dari notebook'),
          ('PERIODE PENELITIAN','1998–2024','27 tahun pengamatan'),
          ('CLUSTER SPASIO-TEMPORAL',number(H.cluster_historical.nunique()) if has_history else '3',
           'Ringkasan historis aktif' if has_history else 'Konfigurasi K-Means (k = 3)')]
    for col,entry in zip(cols,vals):
        with col:stat(*entry)
    st.markdown('<div class="qr-action-label">JELAJAHI PENELITIAN</div>',unsafe_allow_html=True)
    nav_actions=st.columns(5,gap='small')
    for col, (label, dest) in zip(nav_actions,[('Data kejadian','Earthquake Explorer'),('Peta seismik','Seismic Map'),('Analisis ST-GNN','ST-GNN Research'),('Pusat pengetahuan','Knowledge Center'),('Kelola dataset','Data Library')]):
        with col:
            st.button(label,key='home_nav_'+dest,use_container_width=True,
                      on_click=lambda target=dest: st.session_state.update(page=target))
    if not has_catalogue:
        st.markdown('<div class="qr-section-title"><h2>Hubungkan katalog penelitian</h2><span>MEMULAI ANALISIS LENGKAP</span></div>',unsafe_allow_html=True)
        c_upload,c_info=st.columns([1.25,1],gap='large')
        with c_upload:
            uploaded=st.file_uploader('Unggah BMKG_Clean_Final.csv',type=['csv'],key=f'home_upload_events_{st.session_state.home_upload_generation}',help='CSV keluaran Cell 19 Google Colab; file akan disimpan pada data/ setelah lolos validasi.')
            if uploaded is not None:
                try:
                    accept_upload('BMKG_Clean_Final.csv',uploaded.getvalue(),key_kind='home')
                except DatasetError as exc:
                    st.error(str(exc))
            st.caption('Setelah diunggah, file tersimpan pada folder data/ dan otomatis tersedia di seluruh menu, termasuk setelah website dibuka ulang.')
        with c_info:
            st.markdown('''<div class="qr-setup"><h3>Proses integrasi data</h3><ol><li>Unggah katalog historis dari Cell 19.</li><li>Unggah ringkasan grid dan klasifikasi tahunan dari Cell 57–58.</li><li>Gunakan Earthquake Explorer, peta, dan ST-GNN Research untuk analisis lengkap.</li></ol></div>''',unsafe_allow_html=True)
        section('Pratinjau hotspot historis','10 GRID TERTINGGI · OUTPUT NOTEBOOK')
        c_chart,c_map=st.columns([1.0,1.12],gap='medium')
        hist=top_historic()
        with c_chart:
            fig=go.Figure(go.Bar(x=hist.total_event_1998_2024[::-1],y=hist.grid_id[::-1],orientation='h',marker_color=RED,
                         hovertemplate='Grid %{y}<br>%{x:,.0f} kejadian<extra></extra>'))
            fig.update_layout(xaxis_title='Total kejadian 1998–2024',yaxis_title='',margin=dict(t=18,b=35))
            charts(fig,440)
        with c_map:
            st_folium(preview_map('historical'),height=440,use_container_width=True,key='intro_preview_map',returned_objects=[])
        evidence_panel('Apa yang ditunjukkan pratinjau ini?','10 grid dengan total kejadian terbesar 1998–2024',[
            f'Notebook mencatat {number(NOTEBOOK_COUNTS["events"])} kejadian pada 810 grid sepanjang 1998–2024. Grafik ini hanya memuat 10 grid dengan catatan terbanyak dari hasil notebook.',
            f'Grid {hist.iloc[0].grid_id} memiliki {number(hist.iloc[0].total_event_1998_2024)} kejadian pada seluruh periode; setiap kotak peta adalah area 1° × 1°, bukan sebuah titik episenter.',
            'Pratinjau belum menyediakan daftar seluruh kejadian atau filter tahunan. Unggah CSV asli untuk mengaktifkan eksplorasi lengkap; peringkat frekuensi tidak boleh disamakan dengan tingkat risiko bencana.'
        ],'Sumber pratinjau: hasil Cell 22–23 dan output peringkat historis notebook penelitian; bukan katalog live.')
        section('Ringkasan pengujian model','TEST HISTORIS 2021–2024')
        a,b,c,d=st.columns(4)
        for col,entry in zip((a,b,c,d),[
            ('AKURASI KLASIFIKASI','73,49%','Pengujian 2021–2024'),('F1 WEIGHTED','0,7387','Klasifikasi 3 kelas'),
            ('R² REGRESI LOG','0,7749','Pada skala log1p'),('R² REGRESI ASLI','0,2099','Jumlah kejadian per grid')]):
            with col: stat(*entry)
        note('Pratinjau berisi data ringkasan yang memang muncul pada notebook. Statistik keseluruhan per tahun, distribusi magnitudo, dan daftar kejadian hanya muncul setelah CSV historis asli terhubung.')
    else:
        section('Perkembangan kejadian gempa','DARI KATALOG YANG TERHUBUNG')
        section_year=st.select_slider('Periode untuk statistik magnitudo dan kedalaman',options=['Seluruh periode']+list(range(1998,2025)),key='ov_y')
        df=E if section_year=='Seluruh periode' else E[E.year==int(section_year)]
        c1,c2=st.columns([1.5,1],gap='medium')
        with c1:
            st.markdown('<div class="qr-panel-title">Frekuensi kejadian per tahun</div>',unsafe_allow_html=True)
            charts(yearly_fig(E),340)
        with c2:
            st.markdown('<div class="qr-panel-title">Sebaran magnitudo</div>',unsafe_allow_html=True)
            charts(hist_fig(df,'magnitude',35,'Magnitudo',TEAL),340)
        c3,c4=st.columns(2,gap='medium')
        with c3:
            st.markdown('<div class="qr-panel-title">Sebaran kedalaman</div>',unsafe_allow_html=True)
            charts(hist_fig(df,'depth_km',45,'Kedalaman (km)',DARK),290)
        with c4:
            evidence_panel('Interpretasi periode terpilih', 'Seluruh 1998–2024' if section_year=='Seluruh periode' else f'Tahun {section_year}',[
                f'Ditemukan {number(len(df))} kejadian dalam {number(df.grid_id.nunique())} grid pada periode yang dipilih.',
                f'Magnitudo median M {df.magnitude.median():.1f} dan kedalaman median {df.depth_km.median():.1f} km.' if len(df) else 'Tidak ada kejadian dalam rentang pilihan.',
                'Grafik tren tahunan mempertahankan periode penuh sebagai konteks. Grafik magnitudo dan kedalaman mengikuti pilihan pengguna.'
            ],'Perhitungan berasal dari BMKG_Clean_Final.csv, bukan angka ilustratif.')
        section('Peringkat aktivitas spasial','KATALOG HISTORIS')
        hist=H.nsmallest(12,'historical_hotspot_rank') if H is not None else top_historic()
        fig=go.Figure(go.Bar(x=hist.total_event_1998_2024[::-1],y=hist.grid_id[::-1],orientation='h',marker_color=RED))
        fig.update_layout(xaxis_title='Kejadian historis',yaxis_title='Grid')
        charts(fig,370)
        if H is None:
            st.caption('Grafik ini menampilkan 10 grid dari output notebook. Unggah CSV historis untuk memuat seluruh 810 grid.')
    note('Data aktivitas seismik, kelas frekuensi, dan cluster bukan ukuran risiko bencana, dan dashboard ini bukan layanan peringatan dini.')

