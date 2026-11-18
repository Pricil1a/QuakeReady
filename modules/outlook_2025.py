"""Halaman 2025 Outlook; isi dan interaksi mengikuti proyek acuan QuakeReady."""
from __future__ import annotations

def render(context):
    """Render halaman menggunakan dataset dan helper dari app.py."""
    globals().update(context)
    heading('2025 Model Outlook','Keluaran inferensi Hybrid ST-GNN berdasarkan data 2020–2024. Disajikan sebagai pengembangan tambahan dan tidak digunakan sebagai peta peringatan dini.','SUPPLEMENTARY / PROJECTION')
    note('Proyeksi tahun 2025 tidak setara dengan pengamatan aktual 2025. Hindari penggunaan hasil ini untuk keputusan keselamatan atau klaim ketepatan gempa tertentu.')
    if P is None:
        st.info('Pratinjau ini hanya memuat 10 prediksi tertinggi dari output notebook. Unggah STGNN_Analysis_2025.csv untuk melihat seluruh 810 grid.')
        top=top_projection()
        c1,c2=st.columns([1,1.1],gap='medium')
        with c1:
            fig=go.Figure(go.Bar(x=top.predicted_event_2025[::-1],y=top.grid_id[::-1],orientation='h',marker_color=RED))
            fig.update_layout(xaxis_title='Estimasi jumlah kejadian 2025',yaxis_title='Grid')
            charts(fig,440)
        with c2:
            st_folium(preview_map('projection'),height=440,use_container_width=True,key='preview_2025',returned_objects=[])
        st.dataframe(top,hide_index=True,use_container_width=True)
        evidence_panel('Keterbatasan proyeksi','10 grid dengan estimasi tertinggi',[
            'Prediksi menggunakan data historis 2020–2024 sebagai input sliding window lima tahun.',
            'Angka merupakan keluaran regresi model, bukan catatan aktual dan tidak memperkirakan tanggal, magnitudo, atau episenter gempa berikutnya.'
        ])
    else:
        c1,c2,c3=st.columns(3)
        with c1:stat('GRID YANG DIPROYEKSIKAN',number(len(P)),'Area penelitian')
        with c2:stat('ESTIMASI AGREGAT',number(P.predicted_event_2025.sum()),'Hasil model, bukan jumlah aktual')
        with c3:stat('ESTIMASI TERBESAR',number(P.predicted_event_2025.max(),1),'Jumlah kejadian per grid')
        section('Proyeksi frekuensi kejadian','TOP 15 GRID')
        top=P.nlargest(15,'predicted_event_2025')
        fig=go.Figure(go.Bar(x=top.predicted_event_2025[::-1],y=top.grid_id[::-1],orientation='h',marker_color=RED))
        fig.update_layout(xaxis_title='Estimasi jumlah kejadian 2025',yaxis_title='Grid')
        charts(fig,390)
        section('Peta proyeksi','VISUALISASI MODEL')
        pm=build_map(events=None,historical=None,projection=P)
        st_folium(pm,height=510,use_container_width=True,key='map_2025',returned_objects=[])
        st.dataframe(P.nlargest(100,'predicted_event_2025').head(100),hide_index=True,use_container_width=True)
        download(P,'QuakeReady_Proyeksi_2025.csv')

