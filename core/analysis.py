"""Analisis statistik dan pratinjau hasil notebook Google Colab."""
from __future__ import annotations
import numpy as np
import pandas as pd
import folium
from folium.plugins import Fullscreen
from branca.colormap import linear

def annual_counts(events: pd.DataFrame) -> pd.DataFrame:
    """Return calendar-year counts. Years missing from supplied file remain absent."""
    if events is None or len(events) == 0:
        return pd.DataFrame(columns=['year', 'events'])
    return (events.groupby('year').size().rename('events').reset_index()
            .sort_values('year').reset_index(drop=True))

def event_summary(events: pd.DataFrame) -> dict:
    if events is None or len(events) == 0:
        return dict(events=0, grids=0, median_magnitude=np.nan, max_magnitude=np.nan,
                    median_depth=np.nan, shallow=0)
    return dict(events=int(len(events)), grids=int(events.grid_id.nunique()),
                median_magnitude=float(events.magnitude.median()),
                max_magnitude=float(events.magnitude.max()),
                median_depth=float(events.depth_km.median()),
                shallow=int((events.depth_km < 70).sum()))

def catalog_diagnostics(events: pd.DataFrame, hist: pd.DataFrame | None = None,
                        annual: pd.DataFrame | None = None) -> dict:
    """Cross-check loaded artifacts without assuming a national catalogue is complete."""
    issues = []
    if events is None or len(events) == 0:
        return {'catalog': 'not loaded', 'observed_years': [], 'missing_years': [], 'issues': []}
    years = sorted(int(x) for x in events.year.unique())
    missing = sorted(set(range(1998, 2025)).difference(years))
    if missing:
        issues.append('Tidak ada catatan pada tahun: '+', '.join(map(str, missing)))
    unknown = int((~events.grid_id.isin(set(hist.grid_id))).sum()) if hist is not None else None
    hist_total = int(hist.total_event_1998_2024.sum()) if hist is not None else None
    if unknown is not None and unknown:
        issues.append(f'{unknown:,} kejadian katalog berada di luar grid hasil ringkasan.'.replace(',', '.'))
    if hist_total is not None and hist_total != len(events):
        issues.append('Jumlah kejadian katalog dan total grid historis tidak sama. Periksa sumber dan pemrosesan.')
    if annual is not None:
        n_per_grid = int(annual.grid_id.nunique())
        if annual.duplicated(['grid_id', 'year']).any():
            issues.append('Duplikasi grid dan tahun pada CSV tahunan.')
        if hist is not None and n_per_grid != len(hist):
            issues.append('Jumlah grid tahunan tidak sama dengan jumlah grid historis.')
        if hist is not None:
            bygrid = annual.groupby('grid_id')['event_count'].sum()
            cmp = hist.set_index('grid_id').total_event_1998_2024
            shared = bygrid.index.intersection(cmp.index)
            if len(shared) and (~np.isclose(bygrid.loc[shared], cmp.loc[shared])).any():
                issues.append('Rekap jumlah kejadian per grid pada file tahunan dan historis berbeda.')
    return {'catalog': 'loaded','observed_years': years,'missing_years': missing,
            'events': int(len(events)), 'source_grid_count': int(events.grid_id.nunique()),
            'hist_event_sum':hist_total, 'outside_hist_grids': unknown,
            'issues': issues}

def compare_periods(events: pd.DataFrame, first: tuple[int,int], second: tuple[int,int]) -> dict:
    e1=events[events.year.between(*first)]
    e2=events[events.year.between(*second)]
    d1=event_summary(e1); d2=event_summary(e2)
    d1['yearly_rate']=d1['events']/(first[1]-first[0]+1)
    d2['yearly_rate']=d2['events']/(second[1]-second[0]+1)
    return {'left':d1,'right':d2,'ratio':d2['yearly_rate']/d1['yearly_rate'] if d1['yearly_rate'] else None}

def grid_year_detail(events: pd.DataFrame, grid_id: str) -> pd.DataFrame:
    sub=events.loc[events.grid_id == grid_id]
    counts=sub.groupby('year').size().to_dict()
    # 0 means no record in *this supplied catalogue*; never imply safety.
    return pd.DataFrame({'year':list(range(1998,2025)),
                         'events':[int(counts.get(y,0)) for y in range(1998,2025)]})

HISTORICAL_TOP10 = [
    ('-4.0_128.0',8015),('-9.0_116.0',4947),('-3.0_140.0',4646),
    ('-2.0_120.0',4291),('-10.0_119.0',3937),('-9.0_118.0',3815),
    ('-9.0_117.0',3621),('-9.0_110.0',3399),('-8.0_106.0',2858),
    ('-1.0_123.0',2841),
]

PROJECTION_TOP10 = [
    ('-8.0_106.0',119.522565),('0.0_123.0',118.839844),
    ('0.0_122.0',116.703364),('-1.0_123.0',116.036951),
    ('-2.0_122.0',115.634321),('-10.0_119.0',115.269709),
    ('-1.0_121.0',114.884303),('0.0_121.0',114.769186),
    ('-8.0_107.0',114.561942),('-5.0_103.0',114.324541),
]

NOTEBOOK_COUNTS = {'events':217807,'grids':810,'years':27,'first_year':1998,'last_year':2024,
                   'cluster_2025':{0:262,1:372,2:176}}

TEST_METRICS = {'accuracy':0.7348765432098765,'weighted_f1':0.7386649403921516,
                'r2_log':0.7749138652451816,'spearman':0.8319842334337646,
                'mae_count':23.15769769463055,'r2_count':0.20991579761008472}

def parsed_grid(grid):
    a,b=map(float,grid.split('_'))
    return a+.5,b+.5

def top_historic() -> pd.DataFrame:
    df=pd.DataFrame(HISTORICAL_TOP10,columns=['grid_id','total_event_1998_2024'])
    df.insert(0,'historical_hotspot_rank',np.arange(1,len(df)+1))
    df[['latitude','longitude']]=pd.DataFrame([parsed_grid(s) for s in df.grid_id],index=df.index)
    return df

def top_projection() -> pd.DataFrame:
    df=pd.DataFrame(PROJECTION_TOP10,columns=['grid_id','predicted_event_2025'])
    df.insert(0,'hotspot_rank',np.arange(1,len(df)+1))
    df[['latitude','longitude']]=pd.DataFrame([parsed_grid(s) for s in df.grid_id],index=df.index)
    return df

def preview_map(kind='historical'):
    df=top_historic() if kind=='historical' else top_projection()
    column='total_event_1998_2024' if kind=='historical' else 'predicted_event_2025'
    unit='Kejadian tercatat (total 1998–2024)' if kind=='historical' else 'Estimasi kejadian 2025'
    pal=linear.YlOrRd_09.scale(df[column].min(),df[column].max())
    m=folium.Map(location=[-3.1,119],zoom_start=5,tiles='CartoDB positron',control_scale=True)
    Fullscreen().add_to(m)
    fg=folium.FeatureGroup(name='10 grid dari output notebook',show=True)
    for r in df.itertuples(index=False):
        val=float(getattr(r,column))
        bounds=[[float(r.latitude)-.5,float(r.longitude)-.5],
                [float(r.latitude)+.5,float(r.longitude)+.5]]
        color=pal(val)
        popup=f'<b>Grid {r.grid_id}</b><br>{unit}: {val:,.2f}<br><small>Hanya contoh 10 grid dari output notebook</small>'
        folium.Rectangle(bounds=bounds,color=color,weight=1,fill=True,fill_color=color,
                         fill_opacity=.70,tooltip=f'{r.grid_id} · {val:,.1f}',
                         popup=folium.Popup(popup,max_width=250)).add_to(fg)
    fg.add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    return m
