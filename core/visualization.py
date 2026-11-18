"""Peta Folium, layer spasial, dan perhitungan jarak geografis."""
from __future__ import annotations
import numpy as np
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster, Fullscreen
from branca.colormap import linear

ACTIVITY_NAMES = {0:'Tidak tercatat', 1:'Aktivitas sedang', 2:'Aktivitas tinggi'}

ACTIVITY_COLORS = {0:'#94a3b8',1:'#eab308',2:'#e11d48'}

CLUSTER_COLORS = {0:'#7c3aed',1:'#0d9488',2:'#eab308'}

def distance_km(events,lat,lon):
    """Vectorized great-circle distance, kilometers, same rows as events."""
    if events is None or len(events)==0:
        return np.array([],dtype=float)
    lat1=np.radians(events.latitude.to_numpy(dtype=float))
    lon1=np.radians(events.longitude.to_numpy(dtype=float))
    lat2,lon2=np.radians(float(lat)),np.radians(float(lon))
    dlat=lat1-lat2; dlon=lon1-lon2
    a=np.sin(dlat/2)**2+np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 6371.0088*2*np.arcsin(np.minimum(1,np.sqrt(a)))

def in_radius(events,lat,lon,radius_km):
    if events is None or len(events)==0:return events
    dist=distance_km(events,lat,lon)
    return events.loc[dist<=radius_km]

def build_map(events=None, historical=None, annual=None, projection=None,
              mode='Hotspot historis', sample_limit=1200,
              circle=None, show_heatmap=False):
    """Peta HTML Folium; limit hanya untuk marker, bukan statistik/CSV."""
    m=folium.Map(location=[-2.8,118.0],zoom_start=5,tiles='CartoDB positron',control_scale=True)
    Fullscreen(position='topright').add_to(m)
    folium.TileLayer('OpenStreetMap',name='OpenStreetMap').add_to(m)
    if historical is not None and len(historical):
        color_scale=linear.YlOrRd_09.scale(0,max(1,float(historical.total_event_1998_2024.max())))
        fg=folium.FeatureGroup(name='810 grid historis: '+mode,show=True)
        annual_idx=None
        if mode.startswith('Klasifikasi') and annual is not None:
            yr=int(mode.split()[-1]);annual_idx=annual[annual.year==yr].set_index('grid_id')['activity_class'].to_dict()
        for r in historical.itertuples(index=False):
            if mode=='Cluster historis':
                c=CLUSTER_COLORS.get(int(r.cluster_historical),'#64748b')
            elif annual_idx is not None:
                c=ACTIVITY_COLORS.get(int(annual_idx.get(r.grid_id,0)),'#64748b')
            else:
                c=color_scale(float(r.total_event_1998_2024))
            lat,lon=float(r.latitude),float(r.longitude)
            popup=(f'<b>Grid:</b> {r.grid_id}<br><b>Total 1998–2024:</b> {int(r.total_event_1998_2024):,}'
                   f'<br><b>Cluster:</b> {int(r.cluster_historical)}<br><b>Hotspot rank:</b> {int(r.historical_hotspot_rank)}')
            folium.Rectangle(bounds=[[lat-.5,lon-.5],[lat+.5,lon+.5]],color=c,weight=0.45,
                             fill=True,fill_color=c,fill_opacity=.50,
                             tooltip=(
    f'Grid {r.grid_id} · '
    f'{getattr(r, "nama_lokasi", "Lokasi tidak tersedia")} · '
    f'Total {int(r.total_event_1998_2024):,}'
),
                             popup=folium.Popup(popup,max_width=240)).add_to(fg)
        fg.add_to(m)
    if projection is not None and len(projection):
        pred_group=folium.FeatureGroup(name='Proyeksi ST-GNN 2025 (tambahan)',show=True)
        for r in projection.itertuples(index=False):
            folium.CircleMarker([float(r.latitude),float(r.longitude)],radius=4,
                               color='#db2777',fill=True,fill_opacity=.5,weight=.3,
                               tooltip=f'{r.grid_id}: {float(r.predicted_event_2025):.1f} kejadian',
                               popup=f'Proyeksi 2025 · grid {r.grid_id} · {float(r.predicted_event_2025):.2f} kejadian').add_to(pred_group)
        pred_group.add_to(m)
    if events is not None and len(events):
        chosen=events.sample(n=min(int(sample_limit),len(events)), random_state=42) if len(events)>sample_limit else events
        fg=folium.FeatureGroup(name=f'Episenter historis (sampel {len(chosen):,} dari {len(events):,})',show=(historical is None))
        mc=MarkerCluster(disableClusteringAtZoom=9).add_to(fg)
        for r in chosen.itertuples(index=False):
            txt=f'M {float(r.magnitude):.1f} | {str(r.date)[:16]} UTC | {float(r.depth_km):.1f} km'
            folium.CircleMarker([float(r.latitude),float(r.longitude)],radius=3,
                                color='#b91c1c',fill=True,fill_opacity=.7,weight=.3,
                                tooltip=txt,popup=txt).add_to(mc)
        fg.add_to(m)
        if show_heatmap:
            h=folium.FeatureGroup(name='Heatmap historis (sampel)',show=True)
            data=events.sample(n=min(len(events),5000),random_state=42)[['latitude','longitude']].to_numpy().tolist()
            HeatMap(data,radius=12,blur=14).add_to(h);h.add_to(m)
    if circle is not None:
        lat,lon,radius=circle
        c=folium.FeatureGroup(name='Area pencarian radius',show=True)
        folium.Circle([lat,lon],radius=radius*1000,color='#b91c1c',weight=2,fill=True,fill_opacity=.04).add_to(c)
        folium.Marker([lat,lon],tooltip='Pusat pencarian').add_to(c)
        c.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m
