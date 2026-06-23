import streamlit as st
import pandas as pd
from pathlib import Path

SUMMARY_XLSX = Path("multi_site_qa_qc_summary_full.xlsx")

st.set_page_config(layout="wide")
st.title("DayCent Spinup QA/QC Dashboard")

@st.cache_data
def load_summary_xlsx(path_str: str):
    return pd.read_excel(path_str)

inv_path = Path("qaqc_spinup_inventory.csv")
if not inv_path.exists():
    st.error("Missing qaqc_spinup_inventory.csv. Run inventory step first.")
    st.stop()

df = pd.read_csv(inv_path).fillna("")
sites = sorted(df["site"].tolist())

site = st.selectbox("Select site", sites)

view = df[df["site"] == site].copy()
row = view.iloc[0]

st.subheader(f"Site: {site}")
st.write({
    "SOMSC": row["somsc_result"],
    "Biomass": row["biomass_result"],
    "N2O": row["n2o_result"],
    "Biomass livec plots": int(row["biomass_livec_plot_count"]) if str(row["biomass_livec_plot_count"]).isdigit() else row["biomass_livec_plot_count"],
    "N2O summary plots": int(row["n2o_summary_plot_count"]) if str(row["n2o_summary_plot_count"]).isdigit() else row["n2o_summary_plot_count"],
})

def show_img(path_str, label):
    p = Path(path_str)
    if p.exists():
        st.image(str(p), caption=label, use_container_width=True)
    else:
        st.info(f"{label}: not found")

tab_summary, tab1, tab2, tab3 = st.tabs(
    ["QA/QC Summary", "SOMSC", "Biomass", "N2O"]
)

with tab_summary:
    if not SUMMARY_XLSX.exists():
        st.warning(f"Summary file not found: {SUMMARY_XLSX.name}")
    else:
        summary_df = load_summary_xlsx(str(SUMMARY_XLSX))
        site_row = summary_df[summary_df["Site name"].astype(str) == site]
        if site_row.empty:
            st.info(f"No row in {SUMMARY_XLSX.name} for site '{site}'.")
        else:
            sr = site_row.iloc[0]
            step_cols = [
                "Copy common",
                "Extract obs",
                "Spinup sch",
                "Treatment sch",
                "Weather",
                "GEE",
                "DayCent run",
            ]
            st.markdown("**Pipeline steps**")
            st.dataframe(
                sr[step_cols].to_frame("Status").T,
                use_container_width=True,
                hide_index=False,
            )
            st.markdown("**Model checks**")
            st.write(
                {
                    "Biomass": sr["Biomass"],
                    "SOMSC": sr["SOMSC"],
                    "N2O": sr["N2O"],
                    "Overall": sr["Overall"],
                }
            )
            if pd.notna(sr.get("Comments")) and str(sr["Comments"]).strip():
                st.markdown("**Comments**")
                st.text(str(sr["Comments"]))
            if pd.notna(sr.get("Full log path")) and str(sr["Full log path"]).strip():
                st.caption(f"Log: `{sr['Full log path']}`")

        with st.expander("All sites (full table)", expanded=False):
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Excel",
                data=SUMMARY_XLSX.read_bytes(),
                file_name=SUMMARY_XLSX.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

with tab1:
    show_img(row["somsc_spinup_png"], "somsc_timeseries_spinup.png")
    show_img(row["somsc_exp_png"], "somsc_timeseries_exp.png")
    show_img(row["somsc_scatter_png"], "observed_vs_modeled_somsc.png")
    if Path(row["somsc_summary"]).exists():
        st.text(Path(row["somsc_summary"]).read_text(encoding="utf-8", errors="replace"))

with tab2:
    show_img(row["biomass_scatter_png"], "observed_vs_modeled_biomass.png")
    if Path(row["biomass_summary"]).exists():
        st.text(Path(row["biomass_summary"]).read_text(encoding="utf-8", errors="replace"))

with tab3:
    show_img(row["n2o_scatter_png"], "observed_vs_modeled_n2o.png")
    if Path(row["n2o_summary"]).exists():
        st.text(Path(row["n2o_summary"]).read_text(encoding="utf-8", errors="replace"))
