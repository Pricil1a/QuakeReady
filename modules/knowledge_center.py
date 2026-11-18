"""Halaman Knowledge Center; isi dan interaksi mengikuti proyek acuan QuakeReady."""
from __future__ import annotations

def render(context):
    """Render halaman menggunakan dataset dan helper dari app.py."""
    globals().update(context)
    heading('Seismic Knowledge Center','Referensi pengetahuan tentang gempa bumi serta panduan membaca data historis dan hasil pemodelan. Penjelasan dihubungkan langsung dengan statistik dan visualisasi QuakeReady; tanpa kuis atau penilaian.','EDUCATION / SCIENTIFIC LITERACY')
    chapter=st.selectbox('Topik pengetahuan',[
        'Pengantar gempa bumi', 'Magnitudo dan kedalaman', 'Membaca katalog gempa',
        'Distribusi aktivitas di Indonesia', 'Memahami grid dan hotspot',
        'Klasifikasi dan clustering ST-GNN', 'Keselamatan, ketidakpastian, dan sumber'
    ],key='knowledge_chapter')
    if chapter=='Pengantar gempa bumi':
        st.markdown('''<div class="qr-knowledge"><div class="qr-kicker">01 / EARTH SCIENCE FUNDAMENTALS</div><h3>Gempa bumi sebagai peristiwa seismik</h3><p>Gempa bumi adalah getaran yang timbul dari pelepasan energi di dalam bumi, antara lain akibat pergerakan pada patahan dan interaksi lempeng tektonik. Di Indonesia, aktivitas seismik erat berkaitan dengan kondisi tektonik yang kompleks, termasuk zona subduksi dan sistem sesar aktif.</p><p>Dalam katalog, satu kejadian direpresentasikan oleh waktu, posisi episenter, kedalaman, magnitudo, dan metadata pengamatan. Data ini memungkinkan penelitian pola spasial serta temporal, tetapi bukan jadwal atau ramalan gempa berikutnya.</p></div>''',unsafe_allow_html=True)
        st.markdown('**Parameter yang umum ditemukan dalam katalog**')
        for title,body in [('Episenter','Posisi titik di permukaan bumi yang berada di atas sumber gempa. Dicatat menggunakan koordinat lintang dan bujur.'),
                           ('Hiposenter','Lokasi sumber gempa di dalam bumi. Kedalaman menunjukkan jaraknya dari permukaan secara vertikal.'),
                           ('Magnitudo','Ukuran besar gempa sebagai parameter sumber; berbeda dari intensitas guncangan yang dirasakan di suatu tempat.'),
                           ('Intensitas','Tingkat guncangan atau dampak setempat; dipengaruhi jarak, kondisi tanah, bangunan, dan faktor lainnya.')]:
            with st.expander(title):st.write(body)
    elif chapter=='Magnitudo dan kedalaman':
        st.markdown('''<div class="qr-knowledge"><div class="qr-kicker">02 / EVENT PARAMETERS</div><h3>Mengartikan magnitudo dan kedalaman</h3><p>Magnitudo menjelaskan ukuran sumber gempa, sedangkan kedalaman membantu menggambarkan geometri aktivitas seismik. Kedua parameter harus dibaca bersama lokasi dan kondisi setempat; besarnya magnitudo saja tidak cukup untuk menentukan akibat di suatu wilayah.</p><p>Penelitian sering menggunakan kelompok kedalaman dangkal (kurang dari 70 km), menengah (70–300 km), dan dalam (lebih dari 300 km) untuk analisis deskriptif. Pembagian ini adalah kategori kerja, bukan klasifikasi tingkat kerusakan.</p></div>''',unsafe_allow_html=True)
        if E is not None:
            has_map_filters='map_year' in st.session_state
            use_map=st.checkbox('Gunakan filter terakhir dari Seismic Map',value=False,
                                disabled=not has_map_filters,key='learn_from_map',
                                help='Menggunakan tahun, magnitudo, dan kedalaman yang terakhir diatur pada Seismic Map.')
            if use_map:
                yr=st.session_state.get('map_year',(1998,2024))
                dt=E[E.year.between(*yr)].copy()
                mag=st.session_state.get('map_mag')
                depth=st.session_state.get('map_depth')
                if mag is not None: dt=dt[dt.magnitude.between(*mag)]
                if depth is not None: dt=dt[dt.depth_km.between(*depth)]
                scope=f'Filter Seismic Map · Tahun {yr[0]}–{yr[1]}'
                st.caption('Grafik dan penjelasan di bawah memakai kejadian yang sama-sama memenuhi filter peta terakhir, bukan seluruh katalog.')
            else:
                y=st.select_slider('Tahun data untuk ilustrasi',options=['Seluruh periode']+list(range(1998,2025)),key='learn_mag_year')
                dt=E if y=='Seluruh periode' else E[E.year==y]
                scope='Katalog penuh' if y=='Seluruh periode' else f'Tahun {y}'
            if len(dt)==0:
                empty('Tidak ada catatan dalam kombinasi filter','Coba ubah parameter pada Seismic Map atau matikan opsi menggunakan filter peta untuk meninjau katalog lebih luas.')
            else:
                c1,c2=st.columns(2)
                with c1:
                    st.markdown('<div class="qr-panel-title">Magnitudo pada data yang dipilih</div>',unsafe_allow_html=True)
                    charts(hist_fig(dt,'magnitude',40,'Magnitudo',RED),300)
                with c2:
                    st.markdown('<div class="qr-panel-title">Kedalaman pada data yang dipilih</div>',unsafe_allow_html=True)
                    charts(hist_fig(dt,'depth_km',50,'Kedalaman (km)',TEAL),300)
                shallow=int((dt.depth_km<70).sum())
                mid=int(dt.depth_km.between(70,300).sum())
                deep=int((dt.depth_km>300).sum())
                st.markdown(f'<div class="qr-panel"><div class="qr-panel-title">Ringkasan langsung dari katalog</div><div class="qr-panel-sub">Dari {number(len(dt))} kejadian dalam filter, {number(shallow)} tercatat dengan kedalaman kurang dari 70 km, {number(mid)} berada di rentang 70–300 km, dan {number(deep)} lebih dari 300 km.</div></div>',unsafe_allow_html=True)
                evidence_panel('Penjelasan berdasarkan data terpilih',scope,[
                    f'Dari {number(len(dt))} kejadian, magnitudo median M {dt.magnitude.median():.1f} dan maksimum M {dt.magnitude.max():.1f}. Sebaran memperlihatkan frekuensi kejadian pada rentang magnitudo yang tercakup.',
                    f'Kedalaman kurang dari 70 km meliputi {shallow/len(dt)*100:.1f}% kejadian. Klasifikasi kedalaman membantu menggambarkan geometri aktivitas seismik, tetapi bukan prediksi kekuatan guncangan di suatu lokasi.',
                    'Nilai dan grafik mengikuti cakupan filter di atas. Hasil ini berasal dari katalog historis yang terhubung; bukan data gempa real-time.'
                ])
        else:empty('Visualisasi data belum tersedia','Grafik pada topik ini akan menggunakan magnitudo dan kedalaman dari BMKG_Clean_Final.csv setelah katalog dimasukkan.')
    elif chapter=='Membaca katalog gempa':
        st.markdown('''<div class="qr-knowledge"><div class="qr-kicker">03 / DATA LITERACY</div><h3>Dari catatan kejadian menjadi pengetahuan</h3><p>Katalog gempa merupakan tabel pengamatan; setiap baris mewakili satu kejadian yang mempunyai waktu, koordinat, magnitudo, kedalaman, serta identitas. Analisis dimulai dengan memeriksa rentang tanggal, kelengkapan kolom, duplikasi ID, satuan koordinat, dan cakupan sumber data.</p><p>Saat membaca jumlah kejadian per tahun, perhatikan bahwa kemampuan deteksi, jaringan pengamatan, dan ketentuan katalog dapat berubah seiring waktu. Kenaikan jumlah kejadian tercatat tidak selalu menandakan peningkatan aktivitas tektonik dengan besaran yang sama.</p></div>''',unsafe_allow_html=True)
        if E is not None:
            st.markdown('<div class="qr-panel-title">Distribusi tahunan dalam katalog yang digunakan</div>',unsafe_allow_html=True)
            charts(yearly_fig(E),320)
            st.caption(f'Data terhubung: {number(len(E))} baris bersih dengan cakupan tahun {int(E.year.min())}–{int(E.year.max())}.')
        else:empty('Belum ada tabel katalog','Sambungkan BMKG_Clean_Final.csv pada Data Library untuk melihat grafik dan contoh struktur data.')
    elif chapter=='Distribusi aktivitas di Indonesia':
        st.markdown('''<div class="qr-knowledge"><div class="qr-kicker">04 / SEISMICITY OF INDONESIA</div><h3>Persebaran yang tidak merata</h3><p>Kejadian gempa tidak tersebar secara seragam. Frekuensinya berkaitan dengan struktur geologi serta batas dan pergerakan lempeng. Dashboard membantu mengamati konsentrasi aktivitas dalam data historis, bukan memastikan wilayah aman atau tidak aman.</p><p>Gunakan peta interaktif untuk membandingkan grid, lalu periksa kembali waktu dan parameter kejadian pada Earthquake Explorer. Perbedaan jumlah kejadian perlu dibaca dalam konteks rentang pengamatan yang sama.</p></div>''',unsafe_allow_html=True)
        if H is not None:
            peak=H.sort_values('total_event_1998_2024',ascending=False).head(10)
            st.markdown('<div class="qr-panel-title">Sepuluh grid dengan kejadian historis terbanyak</div>',unsafe_allow_html=True)
            st.dataframe(peak[['grid_id','total_event_1998_2024','historical_hotspot_rank']],hide_index=True,use_container_width=True)
            st.caption('Peringkat tersebut berasal dari jumlah kejadian tercatat pada dataset 1998–2024.')
        else:empty('Ringkasan grid belum tersedia','Masukkan QuakeReady_Historis_1998_2024.csv untuk menampilkan contoh hotspot dari data penelitian.')
    elif chapter=='Memahami grid dan hotspot':
        st.markdown('''<div class="qr-knowledge"><div class="qr-kicker">05 / SPATIAL ANALYTICS</div><h3>Membaca hotspot dengan benar</h3><p>QuakeReady mengagregasi kejadian dalam sel spasial 1° × 1°. Satu grid mencakup area, bukan satu titik episenter. Untuk analisis historis, <em>hotspot</em> didefinisikan sebagai grid dengan frekuensi kejadian tercatat relatif tinggi sepanjang 1998–2024.</p><p>Grid berfrekuensi tinggi tidak otomatis lebih berbahaya daripada grid lain; analisis risiko bencana membutuhkan tambahan informasi bahaya, keterpaparan, kerentanan, dan kapasitas.</p></div>''',unsafe_allow_html=True)
        if H is not None:
            sel=st.selectbox('Tinjau data historis per grid',H.sort_values('historical_hotspot_rank').grid_id.tolist(),key='knowledge_grid')
            x=H[H.grid_id==sel].iloc[0]
            a,b,c=st.columns(3)
            with a:stat('TOTAL KEJADIAN',number(x.total_event_1998_2024),'Dalam periode 1998–2024')
            with b:stat('PANGKAT HOTSPOT',number(x.historical_hotspot_rank),'Dari 810 grid')
            with c:stat('CLUSTER',str(int(x.cluster_historical)),'ID K-Means')
            if A is not None:
                seq=A[A.grid_id==sel].sort_values('year')
                fig=go.Figure(go.Bar(x=seq.year,y=seq.event_count,marker_color=TEAL))
                fig.update_layout(xaxis_title='Tahun',yaxis_title='Jumlah kejadian tercatat')
                charts(fig,300)
        else:empty('Analisis grid belum tersedia','Sambungkan file historis 810 grid, lalu pilih salah satu grid untuk membaca data yang tercatat sepanjang periode penelitian.')
    elif chapter=='Klasifikasi dan clustering ST-GNN':
        st.markdown('''<div class="qr-knowledge"><div class="qr-kicker">06 / MODEL INTERPRETATION</div><h3>Dua cara melihat pola aktivitas</h3><p><strong>Klasifikasi</strong> membagi kategori aktivitas tahunan menurut frekuensi kejadian pada tiap grid: kelas 0 (tidak ada kejadian), kelas 1 (1–12), dan kelas 2 (13 atau lebih). Ambang batas kelas 2 ditentukan dari kuantil 90% target training notebook, bukan standar resmi bahaya BMKG.</p><p><strong>Clustering</strong> mengelompokkan embedding 64 dimensi yang dipelajari Hybrid ST-GNN (GCN dan GRU), lalu dianalisis dengan K-Means. Cluster 0, 1, dan 2 adalah identitas kemiripan pola, bukan urutan rendah–tinggi dan bukan tingkat risiko gempa.</p></div>''',unsafe_allow_html=True)
        if A is not None:
            y=st.select_slider('Lihat distribusi kelas pada tahun',options=sorted(A.year.astype(int).unique()),value=2024,key='learn_class_y')
            ct=A[A.year==y].activity_class.value_counts().reindex([0,1,2],fill_value=0)
            fig=go.Figure(go.Bar(x=[ACTIVITY_NAMES[i] for i in range(3)],y=ct.values,marker_color=['#9daab6',GOLD,RED]))
            fig.update_layout(yaxis_title='Jumlah grid',xaxis_title='Kategori aktivitas')
            charts(fig,295)
        else:empty('Kelas tahunan belum tersedia','Grafik akan memuat data dari QuakeReady_Klasifikasi_Tahunan_1998_2024.csv.')
        if H is not None:
            cols=st.columns(3)
            for i,col in enumerate(cols):
                with col:stat(f'CLUSTER {i}',number((H.cluster_historical==i).sum()),'Grid dalam kelompok')
    else:
        st.markdown('''<div class="qr-knowledge"><div class="qr-kicker">07 / RESPONSIBLE INTERPRETATION</div><h3>Data, ketidakpastian, dan kesiapsiagaan</h3><p>Katalog historis memberi pengetahuan mengenai kejadian yang telah tercatat, sementara proyeksi ST-GNN merupakan hasil perhitungan model. Keduanya harus dibedakan dengan jelas. Proyeksi frekuensi tidak dapat digunakan untuk menentukan tanggal, magnitudo, atau titik gempa berikutnya.</p><p>Keselamatan dan kesiapsiagaan memerlukan informasi dari instansi resmi. Ikuti panduan BMKG untuk langkah sebelum, saat, dan setelah gempa; pantau kanal peringatan yang berwenang jika terjadi kejadian nyata.</p><p>Perlu diperhatikan bahwa ketidakhadiran peristiwa dalam satu periode atau grid bukan bukti bahwa wilayah tersebut bebas bahaya gempa.</p></div>''',unsafe_allow_html=True)
    st.markdown('''<div class="qr-linkbox"><strong>Rujukan pengetahuan dan konteks ilmiah</strong><br><a href="https://www.bmkg.go.id/gempabumi/mitigasi/edukasi-gempabumi-tsunami" target="_blank">BMKG — Edukasi Gempa Bumi dan Tsunami</a> &nbsp;·&nbsp; <a href="https://gaia.bmkg.go.id/edukasi-mkg/panduan-kesiapsiagaan-gempabumi-tsunami-dan-sistem-peringatan-dini-bmkg" target="_blank">BMKG — Panduan Kesiapsiagaan</a> &nbsp;·&nbsp; <a href="https://data.bmkg.go.id/gempabumi/" target="_blank">BMKG — Data Gempabumi Terbuka</a><br><span style="display:inline-block;margin-top:8px">Interpretasi statistik dalam halaman ini berasal dari file CSV yang sedang terhubung, bukan hasil pencarian data real-time.</span></div>''',unsafe_allow_html=True)

