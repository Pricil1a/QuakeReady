"""Pembersihan dan normalisasi CSV penelitian QuakeReady."""
from __future__ import annotations
import io
import numpy as np
import pandas as pd

def data_source(upload, path):
    if upload is not None:
        return pd.read_csv(io.BytesIO(upload.getvalue()), low_memory=False)
    if path.exists():
        return pd.read_csv(path, low_memory=False)
    return None

def events_clean(df):
    if df is None:
        return None
    x = df.copy(); x.columns=x.columns.astype(str).str.strip().str.lower()
    mandatory = {'date','latitude','longitude','magnitude','depth_km'}
    missing = mandatory-set(x.columns)
    if missing:
        raise ValueError('Katalog BMKG: kolom wajib tidak ada: '+', '.join(sorted(missing)))
    x['date'] = pd.to_datetime(x['date'], format='mixed', errors='coerce', utc=True)
    # Katalog notebook Colab memakai date (tanggal) dan time_utc (jam) terpisah.
    # Gabungkan jam saat nilai 'date' berisi tanggal tanpa jam, supaya analisis jam UTC
    # dan detail satu kejadian tidak salah terkonsentrasi pada 00:00.
    if 'time_utc' in x.columns:
        clock=pd.to_timedelta(x['time_utc'].astype(str),errors='coerce')
        only_date=x['date'].notna() & (x['date']==x['date'].dt.normalize())
        patch=only_date & clock.notna() & (clock>=pd.Timedelta(0)) & (clock<pd.Timedelta(days=1))
        if patch.any():
            x.loc[patch,'date']=x.loc[patch,'date']+clock.loc[patch]
    for c in ['latitude','longitude','magnitude','depth_km']:
        x[c] = pd.to_numeric(x[c],errors='coerce')
    x = x.dropna(subset=['date','latitude','longitude','magnitude','depth_km'])
    x = x[x.latitude.between(-90,90)&x.longitude.between(-180,180)&x.magnitude.between(0,10)&(x.depth_km>=0)].copy()
    x['year']=x.date.dt.year
    x=x[x.year.between(1998,2024)].copy()
    if 'event_id' in x.columns:
        x=x.drop_duplicates('event_id')
    x['grid_id']=np.floor(x.latitude).astype(str)+'_'+np.floor(x.longitude).astype(str)
    return x

def historic_clean(df):
    if df is None: return None
    x=df.copy();x.columns=x.columns.astype(str).str.strip()
    expected={'grid_id','latitude','longitude','total_event_1998_2024','cluster_historical','historical_hotspot_rank'}
    missing=expected-set(x.columns)
    if missing: raise ValueError('CSV historis: kolom hilang: '+', '.join(sorted(missing)))
    if x.grid_id.duplicated().any():raise ValueError('CSV historis: grid_id duplikat')
    for col in ['latitude','longitude','total_event_1998_2024','cluster_historical','historical_hotspot_rank']:
        x[col]=pd.to_numeric(x[col], errors='coerce')
    if x[list(expected-{'grid_id'})].isna().any().any():raise ValueError('CSV historis: ada nilai numerik kosong')
    return x

def annual_clean(df):
    if df is None:return None
    x=df.copy(); x.columns=x.columns.astype(str).str.strip()
    required={'grid_id','year','event_count','activity_class'}
    if required-set(x.columns):raise ValueError('CSV tahunan: kolom kurang '+str(sorted(required-set(x.columns))))
    for col in ['year','event_count','activity_class']:
        x[col]=pd.to_numeric(x[col],errors='coerce')
    if x[['year','event_count','activity_class']].isna().any().any():raise ValueError('CSV tahunan: data hilang')
    if x.duplicated(['grid_id','year']).any():raise ValueError('CSV tahunan: pasangan grid/tahun duplikat')
    return x

def projection_clean(df):
    if df is None:return None
    x=df.copy();x.columns=x.columns.astype(str).str.strip()
    required={'grid_id','predicted_event_2025','risk_class','cluster'}
    if required-set(x.columns):raise ValueError('CSV prediksi: kolom kurang '+str(sorted(required-set(x.columns))))
    for col in ['predicted_event_2025','risk_class','cluster']:
        x[col]=pd.to_numeric(x[col],errors='coerce')
    if x[list(required-{'grid_id'})].isna().any().any(): raise ValueError('CSV prediksi: ada angka kosong')
    if x.grid_id.duplicated().any():raise ValueError('CSV prediksi: grid_id duplikat')
    if 'latitude' not in x or 'longitude' not in x:
        split=x.grid_id.astype(str).str.split('_',expand=True)
        x['latitude']=pd.to_numeric(split[0],errors='coerce')+.5
        x['longitude']=pd.to_numeric(split[1],errors='coerce')+.5
    return x
