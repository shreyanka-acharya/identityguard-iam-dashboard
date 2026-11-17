import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from iam import initialize, identities, events, joiner, mover, leaver, access_findings, ROLES
from seed_data import seed_enterprise, enterprise_summary, enterprise_table

st.set_page_config(page_title='SageID', page_icon='🔐', layout='wide')
initialize()
st.markdown("""
<style>
:root { color-scheme: light; }
.stApp, [data-testid="stAppViewContainer"] { background: #E8EDE5; color: #46564B; }
[data-testid="stHeader"] { background: #E8EDE5; }
[data-testid="stSidebar"] { background: #D6E3D6; border-right: 1px solid #C0D0C1; }
[data-testid="stSidebar"] * { color: #36483D; }
h1, h2, h3, p, label { color: #46564B; }
[data-testid="stMetric"] {
 background: #F2E9C9; padding: 18px; border-radius: 15px;
 border: 1px solid #E0D8BA; box-shadow: 0 2px 8px rgba(60,75,60,.04);
}
[data-testid="stMetricValue"] { color: #36483D; }
[data-testid="stMetricLabel"] { color: #536457; }
.stButton button, [data-testid="stFormSubmitButton"] button {
 background: #D6E3D6; color: #344735; border-radius: 12px;
 border: 1px solid #B4C8B6; font-weight: 600;
}
.stButton button:hover, [data-testid="stFormSubmitButton"] button:hover {
 background: #C2D5C5; color: #2E4235; border-color: #91B097;
}
div[data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {
 border-radius: 14px; overflow: hidden;
}
[data-testid="stAlert"] { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)
st.title('SageID')
st.markdown('**Identity & Access Management**')
st.caption('Local IAM learning dashboard | Synthetic identities | No production authentication')
page = st.sidebar.radio('Navigate', ['Overview', 'Identities', 'JML Workflows', 'Access Review', 'Audit Log', 'Applications', 'Access Requests'])
st.sidebar.divider()
st.sidebar.caption('Synthetic enterprise demo')
if st.sidebar.button('Load 500 demo employees'):
    created = seed_enterprise()
    st.sidebar.success('Demo records loaded!' if created else 'Demo records already loaded.')
    st.rerun()
people = identities()
summary = enterprise_summary()

if page == 'Overview':
    a,b,c,d = st.columns(4)
    a.metric('Total identities', len(people))
    b.metric('Active', sum(p['status']=='Active' for p in people))
    c.metric('Disabled', sum(p['status']=='Disabled' for p in people))
    d.metric('Active administrators', len(access_findings()))
    e,f,g,h = st.columns(4)
    e.metric('Applications',summary['applications'])
    f.metric('Access assignments',summary['assignments'])
    g.metric('Pending requests',summary['pending'])
    h.metric('Disabled-user grants',summary['orphaned_access'])
    if summary['orphaned_access']:
        st.warning('Demo finding: disabled identities still have application grants. These are review candidates, not verified live accounts.')
    if people:
        df = pd.DataFrame(people)
        st.plotly_chart(px.bar(df.groupby('department',as_index=False).size(), x='department',y='size',title='Identities by department',color='department',color_discrete_sequence=['#E3C7CE','#B8D0BB','#E9D9A6','#D5CDE0']).update_layout(paper_bgcolor='#E8EDE5',plot_bgcolor='#E8EDE5',font_color='#46564B',showlegend=False,yaxis_title='Identities'),use_container_width=True)
        st.plotly_chart(px.pie(df,names='role',title='Role distribution',color_discrete_sequence=['#E3C7CE','#B8D0BB','#E9D9A6','#D5CDE0']).update_layout(paper_bgcolor='#E8EDE5',font_color='#46564B'),use_container_width=True)
elif page == 'Identities':
    st.subheader('Identity directory')
    departments = ['All'] + sorted({p['department'] for p in people})
    department = st.selectbox('Department',departments)
    search = st.text_input('Search name or email')
    filtered = [p for p in people if (department=='All' or p['department']==department) and
                (not search or search.lower() in (p['name']+' '+p['email']).lower())]
    st.caption(f'{len(filtered)} identities shown')
    st.dataframe(pd.DataFrame(filtered),hide_index=True,use_container_width=True)
elif page == 'JML Workflows':
    st.subheader('Joiner - Mover - Leaver')
    join_tab, move_tab, leave_tab = st.tabs(['Onboard', 'Transfer', 'Offboard'])
    with join_tab:
        with st.form('join'):
            name=st.text_input('Full name')
            email=st.text_input('Email')
            department=st.text_input('Department')
            role=st.selectbox('Role',ROLES,index=1)
            submitted=st.form_submit_button('Create identity')
            if submitted:
                try:
                    joiner(name,email,department,role)
                    st.success('Identity created.'); st.rerun()
                except (ValueError,sqlite3.IntegrityError) as exc: st.error(str(exc))
    active=[p for p in people if p['status']=='Active']
    choices={f"{p['id']} - {p['name']} ({p['email']})":p['id'] for p in active}
    with move_tab:
        if choices:
            with st.form('move'):
                selected=st.selectbox('Identity',list(choices),key='move_identity')
                dept=st.text_input('New department')
                role=st.selectbox('New role',ROLES)
                if st.form_submit_button('Update access'):
                    try:
                        mover(choices[selected],dept,role)
                        st.success('Identity updated.'); st.rerun()
                    except ValueError as exc: st.error(str(exc))
        else: st.info('No active identities.')
    with leave_tab:
        if choices:
            with st.form('leave'):
                selected=st.selectbox('Identity to disable',list(choices),key='leave_identity')
                confirm=st.checkbox('Confirm disabling this demo identity')
                if st.form_submit_button('Disable identity'):
                    if not confirm: st.error('Confirmation required.')
                    else:
                        try:
                            leaver(choices[selected]); st.success('Identity disabled.'); st.rerun()
                        except ValueError as exc: st.error(str(exc))
        else: st.info('No active identities.')
elif page == 'Access Review':
    st.subheader('Privileged access review')
    st.info('Review candidates only: active Administrator accounts. This is not a full risk-scoring engine.')
    st.dataframe(pd.DataFrame(access_findings()),hide_index=True,use_container_width=True)
    st.subheader('Access governance findings')
    st.metric('Stale or never-used grants',summary['stale_access'])
    grants = pd.DataFrame(enterprise_table('entitlements'))
    if not grants.empty:
        st.caption('Disabled-user grants require reconciliation. This demo does not provision or revoke real access.')
        st.dataframe(grants[grants['identity_status']=='Disabled'],hide_index=True,use_container_width=True)
elif page == 'Applications':
    st.subheader('Application catalog')
    st.dataframe(pd.DataFrame(enterprise_table('applications')),hide_index=True,use_container_width=True)
    st.subheader('Employee application access')
    grants = pd.DataFrame(enterprise_table('entitlements'))
    if not grants.empty:
        app_filter = st.selectbox('Filter application',['All']+sorted(grants['application'].unique().tolist()))
        if app_filter != 'All': grants = grants[grants['application']==app_filter]
        st.dataframe(grants,hide_index=True,use_container_width=True)
elif page == 'Access Requests':
    st.subheader('Synthetic access request queue')
    st.caption('Read-only request examples; no approval or provisioning engine is connected.')
    requests = pd.DataFrame(enterprise_table('requests'))
    if not requests.empty:
        status = st.selectbox('Status',['All','Pending','Approved','Rejected'])
        if status != 'All': requests = requests[requests['status']==status]
        st.dataframe(requests,hide_index=True,use_container_width=True)
else:
    st.subheader('Audit trail')
    st.dataframe(pd.DataFrame(events()),hide_index=True,use_container_width=True)
