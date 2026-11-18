"""Halaman Data Library; isi dan interaksi mengikuti proyek acuan QuakeReady."""
from __future__ import annotations

def render(context):
    """Render halaman menggunakan dataset dan helper dari app.py."""
    globals().update(context)
    heading('Data Library',
            'Kelola dataset penelitian yang digunakan bersama oleh seluruh fitur QuakeReady. Unggahan valid tersimpan ke folder data/ dan tersedia kembali setelah halaman atau aplikasi dibuka ulang.',
            'WORKSPACE / DATA MANAGEMENT')
    st.markdown("""<div class="qr-knowledge"><h3>Satu sumber data untuk seluruh dashboard</h3><p>Katalog BMKG digunakan oleh Overview, Earthquake Explorer, Seismic Map, Statistical Atlas, dan Knowledge Center. Dua CSV historis memasok klasifikasi, clustering, dan hotspot pada halaman ST-GNN Research dan peta. CSV 2025 memasok halaman 2025 Outlook. Semua menu membaca file yang sama dari direktori <code>data/</code>.</p><p>Setelah file diunggah dan lolos pemeriksaan kolom, file langsung disimpan. Navigasi dan <em>refresh</em> browser tidak menghapusnya pada instalasi Windows/lokal dengan penyimpanan folder yang tetap.</p></div>""",unsafe_allow_html=True)
    linked=sum(x is not None for x in sources.values())
    c1,c2,c3=st.columns(3)
    with c1:stat('DATASET AKTIF',f'{linked} / 4','Dibaca dari data/ pada setiap halaman')
    with c2:stat('KATALOG KEJADIAN',number(len(E)) if E is not None else '—','Baris historis terhubung')
    with c3:stat('GRID ANALISIS',number(len(H)) if H is not None else '—','Grid dari ringkasan historis')
    st.caption('Gunakan navigasi di sebelah kiri atau tombol Beranda / Data Library di bagian atas untuk berpindah tanpa kehilangan unggahan.')
    meta=registry(DATA)
    for filename,(label,cleaner) in FILE_INFO.items():
        with st.container(border=True):
            left,right=st.columns([1.25,1],gap='large')
            with left:
                st.markdown(f'**{label}**')
                st.code(filename,language=None)
                source_path=DATA/filename
                if sources[filename] is not None:
                    st.success(f'Tersimpan dan terhubung · {number(len(sources[filename]))} baris aktif')
                    st.caption('Tersimpan pada data/'+filename)
                    if filename in meta:
                        item=meta[filename]
                        st.caption(f"Terakhir disimpan (UTC): {item.get('saved_at_utc','—')} · SHA-256: {item.get('sha256','')[:12]}…")
                elif filename in errors:
                    st.error('File tersedia tetapi tidak dapat dibaca: '+errors[filename])
                else:
                    st.info('Dataset belum diunggah.')
            with right:
                upload=st.file_uploader(f'Unggah / ganti {label}',type=['csv'],
                    key=f'upload_{filename}_{st.session_state.upload_generations.get(filename,0)}',
                    help='CSV diperiksa sebelum disimpan. Jika gagal, file lama tetap dipertahankan.')
                if upload is not None:
                    try:
                        accept_upload(filename,upload.getvalue(),key_kind='library')
                    except DatasetError as exc:
                        st.error(str(exc))
                if (DATA/filename).exists():
                    confirm=st.checkbox('Konfirmasi penghapusan file tersimpan',key=f'confirm_remove_{filename}')
                    if st.button('Hapus dari penyimpanan',key='delete_'+filename,disabled=not confirm):
                        remove_dataset(DATA,filename)
                        read_clean.clear()
                        st.session_state.upload_generations[filename]=st.session_state.upload_generations.get(filename,0)+1
                        st.session_state.data_notice=f'{filename} telah dihapus dari penyimpanan lokal.'
                        st.rerun()
            if filename in errors:
                st.caption('Unggah ulang CSV yang benar untuk mengganti file bermasalah. File baru hanya mengganti yang lama setelah validasi berhasil.')
    section('Koneksi antardataset','KONDISI DATA TERKINI')
    table=pd.DataFrame([
        {'Menu':'Overview dan Earthquake Explorer','Sumber':'BMKG_Clean_Final.csv','Status':'Siap' if E is not None else 'Menunggu katalog'},
        {'Menu':'Seismic Map — episenter','Sumber':'BMKG_Clean_Final.csv','Status':'Siap' if E is not None else 'Menunggu katalog'},
        {'Menu':'Seismic Map — grid/cluster/hotspot','Sumber':'QuakeReady_Historis_1998_2024.csv','Status':'Siap' if H is not None else 'Menunggu historis'},
        {'Menu':'Statistical Atlas dan Knowledge Center','Sumber':'BMKG_Clean_Final.csv','Status':'Siap' if E is not None else 'Menunggu katalog'},
        {'Menu':'Klasifikasi aktivitas tahunan','Sumber':'QuakeReady_Klasifikasi_Tahunan_1998_2024.csv','Status':'Siap' if A is not None else 'Menunggu kelas'},
        {'Menu':'2025 Outlook','Sumber':'STGNN_Analysis_2025.csv','Status':'Siap' if P is not None else 'Opsional'},
    ])
    st.dataframe(table,hide_index=True,use_container_width=True)
    if E is not None:
        section('Pemeriksaan konsistensi sumber data','DATA YANG TERHUBUNG')
        qa=catalog_diagnostics(E,H,A)
        a,b=st.columns(2)
        with a:stat('CATATAN HISTORIS',number(qa['events']),'Baris katalog terhubung')
        with b:stat('GRID DALAM KATALOG',number(qa['source_grid_count']),'Grid dengan kejadian')
        if qa['issues']:
            for issue in qa['issues']:st.warning(issue)
        else:
            st.success('Pemeriksaan internal antarfail tidak menemukan perbedaan pada aturan yang diuji.')
    note('Penyimpanan ini berada pada folder proyek di perangkat/server tempat aplikasi berjalan. Jika dipublikasikan di Streamlit Community Cloud atau host dengan filesystem sementara, file unggahan dapat hilang saat instance direstart. Untuk deployment publik gunakan penyimpanan eksternal persisten, bukan disk lokal.')

