# Indian Cyclone Dataset — sources, access, alignment

This project builds a **North Indian Ocean (NIO) cyclone dataset**, not a relabeled global dump. The working catalog is IBTrACS v04r01 **NI basin**, cropped to the lab domain:

- Latitude 0°N–30°N  
- Longitude 50°E–110°E  

configured in `configs/data.yaml`.

**Nothing below is fabricated as “already downloaded” except IBTrACS NI**, which the pipeline fetches (~28 MB CSV). ERA5, INSAT, and INCOIS remain **documented, not ingested**, until credentials and storage are available.

---

## Currently ingested

### IBTrACS v04r01 — North Indian Ocean

| Field | Value |
| --- | --- |
| Source | NOAA NCEI IBTrACS |
| URL | https://www.ncei.noaa.gov/products/international-best-track-archive |
| File | `ibtracs.NI.list.v04r01.csv` (~28 MB) |
| Variables | SID, time, lat/lon, WMO and agency wind/pressure, IMD New Delhi grade/wind/pressure, motion, RMW, distance to land |
| Spatial | Point tracks, ~0.1° reporting |
| Temporal | Typically 3-hourly interpolated; agencies often 6-hourly |
| Coverage | NI basin, 1840s–present (modern satellite era from ~1980 is the research subset) |
| Format | CSV (also NetCDF, shapefile) |
| Download | HTTPS, no login |
| License | Redistributable without restriction; cite NOAA/NCEI (doi:10.25921/82ty-9e16) |
| Storage | ~28 MB raw; processed JSON is smaller |

**Indian specialization:** the NI file is the WMO RSMC New Delhi basin, then **spatially cropped** to the Arabian Sea / Bay of Bengal lab box. Wind/pressure prefer `NEWDELHI_*` before WMO/JTWC. Intensity classes use the **IMD** scale (D, DD, CS, SCS, VSCS, ESCS, SuCS).

Splits are **cyclone-level and chronological**:

- Train: seasons ≤ 2016  
- Valid: 2017–2019  
- Test: ≥ 2020  

Observations from the same storm never appear in two splits.

---

## Authoritative sources researched (not bulk-downloaded)

### IMD / RSMC New Delhi best tracks

| Field | Value |
| --- | --- |
| Source | India Meteorological Department, RSMC New Delhi |
| URL | https://rsmcnewdelhi.imd.gov.in/ (Best Track reports) |
| Variables | Operational/best-track positions, intensity, IMD category |
| Period | Yearly reports; compiled workbooks (e.g. 1982–2025 listed on the site) |
| Format | PDF / Excel |
| Access | Public web; awkward for automation |
| License | IMD data — check current site terms; use for research with citation |
| Role | Ground truth for Indian classification; IBTrACS already merges New Delhi fields |

### MOSDAC / ISRO INSAT (3D, 3DR, 3DS)

| Field | Value |
| --- | --- |
| Source | MOSDAC (ISRO) |
| URL | https://mosdac.gov.in |
| Variables | Imager TIR/WV brightness temperature, cloud mask, SST, OLR, precipitation estimates |
| Resolution | Imager IR ~4 km at nadir; full disk ~30 min |
| Format | HDF5 |
| Access | Registered order / API |
| Storage | **Large** (many GB per season if full disk). Download **storm-window crops only**. |
| Role | Satellite channels for detection / structure |

SCORPIO (https://mosdac.gov.in/scorpio/) is ISRO’s experimental NIO cyclone portal — operational reference, not a training dump.

### INCOIS ocean

| Field | Value |
| --- | --- |
| Source | INCOIS |
| URL | https://incois.gov.in (TCHP / SST / SSHA services) |
| Variables | Tropical cyclone heat potential, SST, sea-surface height anomaly |
| Access | WebGIS / products; programmatic access varies |
| Role | Ocean heat for intensification / RI |

### ERA5 (C3S/ECMWF)

| Field | Value |
| --- | --- |
| Source | Copernicus CDS |
| URL | https://cds.climate.copernicus.eu |
| Variables | T, q, z, u, v on pressure levels; MSLP, 10 m wind, precip; SST/waves as available |
| Grid | 0.25° atmosphere (CDS), hourly (use 6-hourly for tracks) |
| Access | ECMWF account + accepted licence + `cdsapi` |
| Storage | A **global** multi-level archive is terabytes. A **NIO crop**, 6-hourly, selected levels, cyclone days only is the prototype budget (tens to hundreds of GB depending on years/levels). |
| Role | Atmospheric predictors for ConvLSTM / transformer patches |

### NOAA OISST v2.1

| Field | Value |
| --- | --- |
| Source | NOAA NCEI |
| Grid | 0.25° daily SST |
| Access | Public NetCDF / ERDDAP |
| Storage | Modest if cropped and limited to cyclone seasons |
| Role | SST when ERA5 SST / INCOIS is unavailable |

### NASA IMERG / GPM

Precipitation; useful later for rainbands. Not ingested.

### JTWC

Present inside IBTrACS `USA_*` columns for NI. Do not scrape extra JTWC products unless needed.

---

## Alignment plan (space and time)

```
IBTrACS fix (lat, lon, t)
        │
        ├─ ERA5: nearest 6-hour analysis, bilinear crop 20°×20° → 64×64
        ├─ OISST: daily field, constant through that UTC day
        ├─ INSAT: nearest 30-min IR, reproject to the same 64×64
        └─ Ocean TCHP: nearest analysis, sample at center + 2° ring
```

All neural training **must wait** until `scripts/align_weather_satellite.py` reports `aligned: true`. The lab currently visualizes a **Holland vortex + seasonal sketch**, labeled as visualization, not observations.

---

## Compatibility risks

- IMD 3-minute wind vs JTWC 1-minute wind (factor ~0.88 often used; we prefer IMD).  
- Agency missing values: fall back WMO then USA.  
- Pre-1980 positions are inhomogeneous — excluded from the research catalog.  
- ERA5 under-represents inner-core winds; satellite IR helps detection more than intensity.
