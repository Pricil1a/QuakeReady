"""Halaman Statistical Atlas; isi dan interaksi mengikuti proyek acuan QuakeReady."""
from __future__ import annotations

import pandas as pd
from core.grid_location import add_grid_location


def render(context):
    """Render halaman menggunakan dataset dan helper dari app.py."""

    # Salin konteks agar tidak mengubah objek context milik app.py.
    context = dict(context)

    # Tambahkan nama lokasi grid ke katalog untuk informasi hover globe.
    # Jika mapping gagal dimuat, halaman statistik tetap berjalan seperti semula.
    event_data = context.get("E")
    if (
        isinstance(event_data, pd.DataFrame)
        and "grid_id" in event_data.columns
    ):
        needs_location = (
            "nama_lokasi" not in event_data.columns
            or event_data["nama_lokasi"].isna().all()
            or event_data["nama_lokasi"].astype("string").str.strip().eq("").all()
        )
        if needs_location:
            try:
                context["E"] = add_grid_location(event_data)

            except Exception:
                # Jangan sampai kegagalan metadata lokasi merusak atlas statistik.
                context["E"] = event_data

    globals().update(context)

    heading('Statistical Atlas',
            'Membaca dinamika katalog BMKG melalui tren tahunan, distribusi magnitudo dan kedalaman, pola bulanan, dan perbandingan antarperiode.',
            'RESEARCH / HISTORICAL STATISTICS')
    if E is None:
        st.info('Halaman atlas akan menghitung distribusi tahunan, magnitudo dan kedalaman ketika katalog lengkap dimuat. Data yang tersedia saat ini adalah hasil agregasi 10 grid teratas dari notebook.')
        hist=top_historic()
        fig=go.Figure(go.Bar(x=hist.total_event_1998_2024[::-1],y=hist.grid_id[::-1],orientation='h',marker_color=TEAL))
        fig.update_layout(xaxis_title='Total kejadian 1998–2024',yaxis_title='Grid')
        charts(fig,470)
        evidence_panel('Memahami grafik agregasi','Peringkat 10 grid, bukan seluruh 810',[
            'Data ini menghitung jumlah kejadian per grid sepanjang 27 tahun, bukan jumlah per tahun dan bukan data magnitudo individual.',
            'Distribusi magnitudo, profil kedalaman, dan deret waktu tidak dapat dihitung dari tabel agregasi 10 grid. Unggah katalog historis untuk statistik tersebut.'
        ],'Nilai berasal dari output notebook; tidak ada kejadian buatan.')
    else:
        y1,y2=st.slider('Periode statistik',1998,2024,(1998,2024),key='stat_years')
        mag_start,mag_end=st.slider('Magnitudo dalam statistik',
                                   float(np.floor(E.magnitude.min()*10)/10),
                                   float(np.ceil(E.magnitude.max()*10)/10),
                                   (float(np.floor(E.magnitude.min()*10)/10),float(np.ceil(E.magnitude.max()*10)/10)),
                                   step=0.1,key='stat_mag')
        active=E[E.year.between(y1,y2)&E.magnitude.between(mag_start,mag_end)]
        s0=event_summary(active)
        c1,c2,c3,c4=st.columns(4,gap='small')
        for col,entry in zip([c1,c2,c3,c4],[
            ('KEJADIAN',number(s0['events']),'Dalam filter'),
            ('GRID TERAMATI',number(s0['grids']),'Pencatatan dalam filter'),
            ('MAGNITUDO MEDIAN',number(s0['median_magnitude'],1),'Ukuran sumber'),
            ('KEDALAMAN MEDIAN',number(s0['median_depth'],1)+' km' if len(active) else '—','Kedalaman hiposenter')]):
            with col:stat(*entry)
        if len(active):
            st.markdown('<div class="qr-panel-title">Tren tahunan berdasarkan filter aktif</div>',unsafe_allow_html=True)
            charts(yearly_fig(active),355)
            a,b=st.columns(2,gap='medium')
            with a:
                st.markdown('<div class="qr-panel-title">Sebaran magnitudo</div>',unsafe_allow_html=True)
                charts(hist_fig(active,'magnitude',38,'Magnitudo',TEAL),320)
            with b:
                st.markdown('<div class="qr-panel-title">Sebaran kedalaman</div>',unsafe_allow_html=True)
                charts(hist_fig(active,'depth_km',44,'Kedalaman (km)',DARK),320)
            left,right=st.columns(2,gap='medium')
            with left:
                monthly=active.groupby(active.date.dt.month).size().reindex(range(1,13),fill_value=0)
                fig=go.Figure(go.Bar(x=list(range(1,13)),y=monthly.values,marker_color=RED))
                fig.update_layout(xaxis_title='Bulan (UTC)',yaxis_title='Kejadian tercatat')
                st.markdown('<div class="qr-panel-title">Distribusi menurut bulan</div>',unsafe_allow_html=True)
                charts(fig,295)
            with right:
                hourly=active.groupby(active.date.dt.hour).size().reindex(range(24),fill_value=0)
                fig=go.Figure(go.Bar(x=list(range(24)),y=hourly.values,marker_color=TEAL))
                fig.update_layout(xaxis_title='Jam (UTC)',yaxis_title='Kejadian tercatat')
                st.markdown('<div class="qr-panel-title">Distribusi menurut jam UTC</div>',unsafe_allow_html=True)
                charts(fig,295)
            years_ct=active.groupby('year').size()
            evidence_panel('Ringkasan statistik periode aktif',f'{y1}–{y2} · M {mag_start:.1f}–{mag_end:.1f}',[
                f'Terdapat {number(len(active))} kejadian dalam {number(active.grid_id.nunique())} grid pada katalog yang dipilih. Proporsinya {len(active)/len(E)*100:.2f}% dari seluruh baris katalog yang terhubung.',
                f'Tahun dengan kejadian terbanyak dalam seleksi adalah {int(years_ct.idxmax())} ({number(int(years_ct.max()))} catatan). Ini tidak otomatis mengindikasikan peningkatan bahaya gempa pada tahun tersebut.',
                f'Di antara kejadian terpilih, {number(int((active.depth_km < 70).sum()))} tercatat memiliki kedalaman kurang dari 70 km. Magnitudo median M {active.magnitude.median():.1f}; nilai terbesar M {active.magnitude.max():.1f}.',
                'Distribusi waktu merujuk UTC dalam katalog. Peningkatan jumlah gempa tercatat dapat dipengaruhi perubahan cakupan pengamatan, sehingga data tahunan perlu ditafsirkan hati-hati.'
            ],'Perhitungan berdasarkan file BMKG_Clean_Final.csv dan parameter pilihan pengguna. Bukan katalog real-time.')
            section('Sebaran episenter pada globe', 'VISUALISASI SPASIAL TAMBAHAN')
            # Tampilan globe memakai subsampel tetap, tidak menghitung ulang total kejadian.
            globe_events=active.sample(min(len(active),1800),random_state=17) if len(active)>1800 else active

            # Tambahkan grid dan nama lokasi pada teks hover; nilai statistik/marker tidak berubah.
            grid_values = (
                globe_events["grid_id"].fillna("—").astype(str)
                if "grid_id" in globe_events.columns
                else pd.Series("—", index=globe_events.index)
            )
            location_values = (
                globe_events["nama_lokasi"].fillna("—").astype(str)
                if "nama_lokasi" in globe_events.columns
                else pd.Series("—", index=globe_events.index)
            )
            hover_text = [
                f'M {m:.1f} | {d:.0f} km | {str(t)[:10]} | Grid {g} | Lokasi: {loc}'
                for m,d,t,g,loc in zip(
                    globe_events.magnitude,
                    globe_events.depth_km,
                    globe_events.date,
                    grid_values,
                    location_values,
                )
            ]

            globe=go.Figure(go.Scattergeo(
                lat=globe_events.latitude,lon=globe_events.longitude,mode='markers',
                marker=dict(size=4,color=globe_events.magnitude,colorscale='YlOrRd',
                            cmin=float(E.magnitude.min()),cmax=float(E.magnitude.max()),
                            showscale=True,colorbar=dict(title='M',thickness=12)),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>'
            ))
            globe.update_geos(projection_type='orthographic',projection_rotation=dict(lon=115,lat=-5),
                showland=True,landcolor='#f0f3f6',showocean=True,oceancolor='#dbe7f0',
                showcountries=True,countrycolor='#a9b8c6',showcoastlines=True,coastlinecolor='#8598ab',
                bgcolor='white')
            globe.update_layout(height=440,margin=dict(l=5,r=5,t=10,b=10),paper_bgcolor='white')
            st.plotly_chart(globe,use_container_width=True,config={'displaylogo':False})
            st.caption(f'Globe memvisualisasikan {number(len(globe_events))} titik dari {number(len(active))} kejadian terfilter. Distribusi ini bersifat sampel untuk kinerja antarmuka dan bukan peta kepadatan terkalibrasi.')
            section('Perbandingan dua periode','PERBANDINGAN FREKUENSI TAHUNAN')
            cp1,cp2=st.columns(2)
            p1=cp1.slider('Periode pertama',1998,2024,(2005,2014),key='cmp_period_1')
            p2=cp2.slider('Periode kedua',1998,2024,(2015,2024),key='cmp_period_2')
            result=compare_periods(active,p1,p2)
            cpa,cpb=st.columns(2)
            with cpa:stat(f'RATA-RATA TAHUNAN {p1[0]}–{p1[1]}',number(result['left']['yearly_rate'],1),'Kejadian tercatat per tahun')
            with cpb:stat(f'RATA-RATA TAHUNAN {p2[0]}–{p2[1]}',number(result['right']['yearly_rate'],1),'Kejadian tercatat per tahun')
            evidence_panel('Perbandingan rentang observasi',f'Periode {p1[0]}–{p1[1]} vs {p2[0]}–{p2[1]}',[
                f'Periode pertama memiliki {number(result["left"]["events"])} catatan dengan rata-rata {result["left"]["yearly_rate"]:.1f} per tahun. Periode kedua memiliki {number(result["right"]["events"])} catatan dengan rata-rata {result["right"]["yearly_rate"]:.1f} per tahun.',
                'Rata-rata tahunan digunakan karena jumlah tahun dalam dua periode dapat berbeda. Perbandingan dilakukan pada filter magnitudo yang sama.',
                'Selisih frekuensi katalog tidak cukup untuk menyimpulkan perubahan laju kejadian tektonik tanpa mempertimbangkan jaringan deteksi dan metode pengumpulan data.'
            ])
            download(active,'QuakeReady_Statistical_Atlas_Filtered.csv')
        else:
            empty('Tidak ada hasil untuk kombinasi ini','Perluas periode atau rentang magnitudo untuk menampilkan statistik.')
