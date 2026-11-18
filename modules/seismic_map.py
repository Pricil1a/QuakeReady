"""Halaman Seismic Map; isi dan interaksi mengikuti proyek acuan QuakeReady."""
from __future__ import annotations
from core.grid_location import add_grid_location

def render(context):
    """Render halaman menggunakan dataset dan helper dari app.py."""

    context = dict(context)

    # Menambahkan nama lokasi ke dataset grid
    for name in ("H", "A", "E"):
        df = context.get(name)

        if df is not None and "grid_id" in df.columns:
            context[name] = add_grid_location(df)

    globals().update(context)
    heading('Seismic Map',
            'Eksplorasi kejadian gempa dan pola aktivitas spasial Indonesia. Filter dan parameter pencarian terhubung langsung dengan peta, statistik, serta penjelasan di halaman ini.',
            'GEOSPATIAL / INTERACTIVE OBSERVATORY')
    if E is None and H is None:
        st.info('Peta ini merupakan pratinjau 10 hotspot historis dari notebook. Masukkan CSV katalog dan ringkasan grid di Data Library untuk mengaktifkan filter lengkap.')
        st_folium(preview_map('historical'),height=510,use_container_width=True,key='map_history_preview',returned_objects=[])
        evidence_panel('Memahami pratinjau historis','10 grid historis teratas',[
            'Setiap persegi pada peta menunjukkan area grid satu derajat lintang × satu derajat bujur. Warna menunjukkan frekuensi kejadian tercatat sepanjang 1998–2024, bukan lokasi atau waktu gempa yang akan terjadi.',
            'Pratinjau tidak memuat seluruh 810 grid dan belum dapat difilter menurut tanggal, magnitudo, atau kedalaman. Masukkan BMKG_Clean_Final.csv dan QuakeReady_Historis_1998_2024.csv agar peta lengkap tersedia.'
        ],'Sumber: ringkasan hasil notebook penelitian; bukan pemantauan real-time.')
    else:
        st.markdown('<div class="qr-map-intro"><strong>PANDUAN PENGGUNAAN</strong><span>Atur parameter di sebelah kiri. Peta dan ringkasan di sebelah kanan berubah otomatis. Data yang disaring adalah catatan episenter, sedangkan warna grid menunjukkan layer analisis yang dipilih. Scroll ke bagian Hasil dan Interpretasi untuk melihat arti setiap perubahan.</span></div>',unsafe_allow_html=True)
        left,right=st.columns([0.95,2.1],gap='large')
        with left:
            with st.container(border=True):
                st.markdown('<div class="qr-config-heading">PENGATURAN PETA</div>',unsafe_allow_html=True)
                modes=['Hotspot historis','Cluster historis'] if H is not None else ['Episenter saja']
                if H is not None and A is not None:
                    modes += [f'Klasifikasi {y}' for y in sorted(A.year.astype(int).unique(),reverse=True)]
                mode=st.selectbox('Layer analisis',modes,key='map_layer')
                if mode=='Hotspot historis':
                    st.caption('Warna menunjukkan banyaknya kejadian selama 1998–2024 pada tiap grid. Filter episenter tidak mengubah jumlah historis di layer ini.')
                elif mode=='Cluster historis':
                    st.caption('Warna menunjukkan kelompok pola embedding ST-GNN. Angka cluster bukan urutan risiko atau bahaya.')
                elif mode.startswith('Klasifikasi'):
                    st.caption('Warna menandai kelas frekuensi tahunan: tidak tercatat, 1–12, atau minimal 13 kejadian.')
                else:
                    st.caption('Tampilkan titik episenter tercatat dari katalog tanpa overlay grid.')
                show_heat=st.checkbox('Tampilkan heatmap episenter',value=False,disabled=E is None,key='map_heat')
                st.caption('Heatmap memperlihatkan kepadatan titik visualisasi, bukan tingkat risiko bencana.')
                sample=st.select_slider('Maksimum marker episenter',options=[300,600,1000,2000,3500],value=1000,key='map_marker_count')
                st.caption('Batas marker hanya untuk performa tampilan. Statistik dan ekspor tetap memakai seluruh kejadian yang lolos filter.')

            filtered=E
            years=(1998,2024)
            if E is not None:
                with st.container(border=True):
                    st.markdown('<div class="qr-config-heading">FILTER KATALOG</div>',unsafe_allow_html=True)
                    years=st.slider('Rentang tahun kejadian',1998,2024,(1998,2024),key='map_year')
                    filtered=E[E.year.between(*years)]
                    filtered=range_slider(filtered,'magnitude','Magnitudo',key='map_mag',bounds_df=E)
                    filtered=range_slider(filtered,'depth_km','Kedalaman (km)',key='map_depth',bounds_df=E)
                    st.caption('Ketiga filter diterapkan sekaligus. Semua statistik kejadian dan penanda episenter mengikuti pilihan ini; layer grid historis tetap memakai sumbernya sendiri.')
            else:
                st.markdown('<div class="qr-panel-sub">Katalog BMKG belum dimuat. Filter magnitudo, kedalaman, dan tahun memerlukan BMKG_Clean_Final.csv.</div>',unsafe_allow_html=True)

            circle=None
            with st.container(border=True):
                st.markdown('<div class="qr-config-heading">PENCARIAN BERDASARKAN RADIUS</div>',unsafe_allow_html=True)
                use=st.checkbox('Aktifkan pencarian radius',key='map_circle_on')
                c1,c2=st.columns(2)
                lat=c1.number_input('Lintang pusat (°)',value=-6.2,min_value=-15.,max_value=10.,step=.1,key='map_circle_lat')
                lon=c2.number_input('Bujur pusat (°)',value=106.8,min_value=94.,max_value=142.,step=.1,key='map_circle_lon')
                radius=st.slider('Radius (km)',20,1000,200,20,key='map_circle_radius')
                st.caption('Menghitung jarak antara pusat pilihan dan setiap episenter terfilter menggunakan haversine; bukan jangkauan kerusakan gempa.')
                if use:circle=(lat,lon,radius)

        with right:
            st.markdown('<div class="qr-map-head"><strong>Peta distribusi seismik Indonesia</strong><span>1998–2024 · Katalog dan grid penelitian</span></div>',unsafe_allow_html=True)
            total_filter=len(filtered) if filtered is not None else 0
            if E is not None:
                c1,c2,c3=st.columns(3,gap='small')
                with c1:st.metric('Kejadian hasil filter',number(total_filter))
                with c2:st.metric('Grid terwakili',number(filtered.grid_id.nunique()))
                with c3:st.metric('Marker ditampilkan',number(min(total_filter,int(sample))))
            else:
                st.caption('Layer grid penelitian sedang ditampilkan; data episenter belum terhubung.')
            m=build_map(events=filtered,historical=H,annual=A,mode=mode,circle=circle,
                        sample_limit=sample,show_heatmap=show_heat)
            click=st_folium(m,height=505,use_container_width=True,key='map_historical',returned_objects=['last_object_clicked'])
            if click and isinstance(click.get('last_object_clicked'),dict):
                obj=click['last_object_clicked']
                st.caption('Koordinat titik peta yang diklik: '+str(obj.get('lat','—'))+', '+str(obj.get('lng','—'))+'. Klik bidang grid untuk melihat nilai historis melalui popup.')
            else:
                st.caption('Klik marker untuk detail episenter atau bidang grid untuk melihat agregasi. Anda juga dapat menyalakan atau mematikan layer melalui kontrol peta.')

        section('Hasil dan interpretasi','DIPERBARUI OTOMATIS SETELAH FILTER DIUBAH')
        if E is not None:
            mm=st.session_state.get('map_mag',(float(E.magnitude.min()),float(E.magnitude.max())))
            dd=st.session_state.get('map_depth',(float(E.depth_km.min()),float(E.depth_km.max())))
            messagescope=(f'Tahun {years[0]}–{years[1]} · '
                f'M {mm[0]:.1f}–{mm[1]:.1f} · '
                f'{dd[0]:.0f}–{dd[1]:.0f} km')
            describe_event_selection(filtered,E,messagescope)
        describe_map_selection(filtered,H,A,mode,show_heat,sample,circle)
        if circle is not None:
            if E is None:
                st.info('Lingkaran pencarian terlihat pada peta. Untuk menghitung catatan di dalam radius, unggah katalog historis BMKG.')
            else:
                inside=in_radius(filtered,*circle)
                if len(inside):
                    ranked=inside.copy()
                    ranked['distance_km']=distance_km(ranked,circle[0],circle[1])
                    a,b,c=st.columns(3)
                    with a:stat('DALAM RADIUS',number(len(ranked)),'Kejadian setelah filter')
                    with b:stat('JARAK TERDEKAT',number(ranked.distance_km.min(),1)+' km','Dari pusat pencarian')
                    with c:stat('JARAK TERJAUH',number(ranked.distance_km.max(),1)+' km','Masih di dalam radius')
                    cols=[c for c in ['event_id','date','magnitude','depth_km','distance_km','grid_id'] if c in ranked.columns]
                    st.markdown('**Contoh kejadian dalam radius**')
                    st.dataframe(ranked.nsmallest(12,'distance_km')[cols],hide_index=True,use_container_width=True)
                    evidence_panel('Makna hasil pencarian geografis',f'Radius {radius} km dari ({lat:.2f}, {lon:.2f})',[
                        f'Sebanyak {number(len(inside))} kejadian yang memenuhi filter berada dalam radius {number(radius)} km dari pusat pencarian. Jarak minimum {ranked.distance_km.min():.1f} km dan maksimum {ranked.distance_km.max():.1f} km dihitung terhadap lokasi episenter yang tercatat.',
                        'Hasil ini hanya pemilihan data secara geografis. Jarak episenter saja tidak cukup untuk memperkirakan guncangan, dampak, atau menentukan apakah sebuah tempat aman.'
                    ],'Sumber: katalog yang terhubung; perhitungan jarak haversine dalam kilometer.')
                else:
                    empty('Tidak ditemukan kejadian dalam radius',
                          'Tidak ada kejadian tercatat yang sekaligus memenuhi rentang waktu, magnitudo, kedalaman, dan radius. Ini tidak menyatakan bahwa area tersebut bebas bahaya gempa.')
        if H is not None:
            section('Mengenali satu grid secara mendalam','KONTEKS HISTORIS DAN TAHUNAN')
            grid_options=H.sort_values('historical_hotspot_rank').grid_id.astype(str).tolist()
            focused=st.selectbox('Pilih grid untuk penjelasan',grid_options,key='map_focus_grid',
                help='Pilih satu dari 810 grid untuk membaca data jumlah kejadian, cluster, dan keterwakilan dalam filter aktif.')
            
            hrow = H.loc[
                H.grid_id.astype(str) == focused
            ].iloc[0]

            in_grid = 0 if filtered is None else int(
                (filtered.grid_id.astype(str) == focused).sum()
            )

            # Mengambil nama lokasi grid
            location_name = hrow.get(
                "nama_lokasi",
                "Nama lokasi belum tersedia"
            )

            if location_name is None or str(location_name).strip() in ("", "nan"):
                location_name = "Nama lokasi belum tersedia"

            # Menyusun interpretasi grid
            detail = [
                f"Nama lokasi: {location_name}.",
                f"Grid {focused} mencatat {number(hrow.total_event_1998_2024)} kejadian selama 1998–2024, dengan peringkat hotspot historis {number(hrow.historical_hotspot_rank)} dari {number(len(H))} grid.",
                f"Grid termasuk Cluster {int(hrow.cluster_historical)} menurut embedding ST-GNN. Nomor cluster menunjukkan kemiripan fitur, tidak membuktikan tingkat bahaya."
            ]

            if filtered is not None:
                detail.append(
                    f"Pada rentang tahun, magnitudo, dan kedalaman yang Anda pilih, terdapat {number(in_grid)} kejadian dari katalog di grid ini."
                )

            if A is not None:
                y = years[1] if E is not None else 2024
                one = A[
                    (A.grid_id.astype(str) == focused) &
                    (A.year == y)
                ]

                if not one.empty:
                    yrow = one.iloc[0]
                    detail.append(
                        f"Pada tahun {y}, jumlah kejadian historis pada grid ini adalah {number(yrow.event_count)} dan kelas aktivitasnya {int(yrow.activity_class)}."
                    )

            evidence_panel(
                'Interpretasi grid pilihan',
                f'{focused} — {location_name}',
                detail,
                'Sumber: ringkasan grid historis, katalog historis, dan tabel kelas tahunan jika tersedia.'
            )

            detail=[
                f'Grid {focused} mencatat {number(hrow.total_event_1998_2024)} kejadian selama 1998–2024, dengan peringkat hotspot historis {number(hrow.historical_hotspot_rank)} dari {number(len(H))} grid.',
                f'Grid termasuk Cluster {int(hrow.cluster_historical)} menurut embedding ST-GNN. Nomor cluster menunjukkan kemiripan fitur, tidak membuktikan tingkat bahaya.',
            ]
            if filtered is not None:
                detail.append(f'Pada rentang tahun, magnitudo, dan kedalaman yang Anda pilih, terdapat {number(in_grid)} kejadian dari katalog di grid ini. Angka ini dapat lebih kecil daripada total historis yang tidak difilter.')
            if A is not None:
                y=years[1] if E is not None else 2024
                one=A[(A.grid_id.astype(str)==focused)&(A.year==y)]
                if not one.empty:
                    yrow=one.iloc[0]
                    detail.append(f'Pada tahun {y}, jumlah kejadian historis pada grid ini adalah {number(yrow.event_count)} dan kelas aktivitasnya {int(yrow.activity_class)}. Kelas merupakan kategori frekuensi berdasarkan ambang penelitian.')
            evidence_panel('Interpretasi grid pilihan',f'Grid {focused}',detail,
                           'Sumber: ringkasan grid historis, katalog historis, dan tabel kelas tahunan jika tersedia.')
            def open_grid_learning():
                st.session_state['learning_grid_preference']=focused
                st.session_state['knowledge_grid']=focused
                st.session_state['knowledge_chapter']='Memahami grid dan hotspot'
                st.session_state['page']='Knowledge Center'
            st.button('Baca penjelasan ilmiah tentang grid dan hotspot',on_click=open_grid_learning,
                      key='map_to_learning')
        note('Data historis dan model digunakan untuk pembelajaran dan penelitian. QuakeReady tidak memprediksi waktu, magnitudo, atau episenter gempa berikutnya dan bukan layanan peringatan dini.')

