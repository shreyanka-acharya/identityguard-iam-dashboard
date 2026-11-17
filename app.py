import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from iam import initialize, identities, events, joiner, mover, leaver, access_findings, ROLES
from seed_data import seed_enterprise, enterprise_summary, enterprise_table

st.set_page_config(page_title='Accessly', page_icon='🔐', layout='wide')
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
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
[data-testid="stMetric"] { min-height: 115px; }
[data-testid="stMetricLabel"] p { font-size: .9rem; }
[data-testid="stPlotlyChart"] { background: #F1F3EC; }
</style>
""", unsafe_allow_html=True)
st.title('Accessly')
st.markdown('**A simpler way to explore identities, roles, and access.**')
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

def gauge(title, value, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(value, 1),
        number={"suffix": "%", "font": {"size": 29, "color": "#46564B"}},
        title={"text": title, "font": {"size": 15, "color": "#46564B"}},
        gauge={"axis": {"range": [0, 100], "tickwidth": 0},
               "bar": {"color": color, "thickness": 0.38},
               "bgcolor": "#E1E6DC", "borderwidth": 0}
    ))
    fig.update_layout(height=235, margin=dict(l=25,r=25,t=55,b=10),
                      paper_bgcolor="#F1F3EC",font_color="#46564B")
    return fig


if page == 'Overview':
    st.subheader('Identity governance overview')
    department = st.selectbox('Department', ['All departments'] + sorted({p['department'] for p in people}))
    selected = [p for p in people if department == 'All departments' or p['department'] == department]
    selected_ids = {p['id'] for p in selected}
    active = [p for p in selected if p['status'] == 'Active']
    grants = enterprise_table('entitlements')
    grants = [g for g in grants if department == 'All departments' or g['department'] == department]
    requests = enterprise_table('requests')
    if department != 'All departments':
        requests = [r for r in requests if r['department'] == department]
    pending = sum(r['status'] == 'Pending' for r in requests)
    disabled_grants = sum(g['identity_status'] == 'Disabled' for g in grants)
    stale_grants = sum(g['identity_status'] == 'Active' and
                       (not g['last_used_at'] or
                        (pd.Timestamp.now(tz='UTC') - pd.to_datetime(g['last_used_at'], utc=True)).days > 90)
                       for g in grants)
    active_rate = 100 * len(active) / len(selected) if selected else 0
    hygiene_rate = 100 * (len(grants) - disabled_grants - stale_grants) / len(grants) if grants else 0
    decision_count = sum(r['status'] != 'Pending' for r in requests)
    review_rate = 100 * decision_count / len(requests) if requests else 0

    a,b,c,d = st.columns(4)
    a.metric('Total identities', len(selected))
    b.metric('Active identities', len(active))
    c.metric('Application grants', len(grants))
    d.metric('Pending requests', pending)

    left, mid, right = st.columns([1,1,1])
    with left:
        st.plotly_chart(gauge('Active identity rate',active_rate,'#AFC9B2'),use_container_width=True)
    with mid:
        st.plotly_chart(gauge('Access hygiene',hygiene_rate,'#DDBAC4'),use_container_width=True)
    with right:
        st.plotly_chart(gauge('Requests decided',review_rate,'#E4D095'),use_container_width=True)

    x,y,z = st.columns(3)
    x.metric('Disabled identities',len(selected)-len(active))
    y.metric('Disabled-user grants',disabled_grants)
    z.metric('Stale active grants',stale_grants)
    st.caption('Access hygiene = grants not flagged as stale or belonging to disabled identities. '
               'Requests decided = approved or rejected sample requests. These are demo indicators, not formal compliance scores.')

    left,right = st.columns([1.45,1])
    with left:
        st.markdown('#### Application access distribution')
        if grants:
            chart_df = pd.DataFrame(grants).groupby('application').size().reset_index(name='grants')
            chart_df = chart_df.sort_values('grants',ascending=True)
            fig = px.bar(chart_df,x='grants',y='application',orientation='h',
                         color_discrete_sequence=['#AFC9B2'])
            fig.update_layout(height=420,paper_bgcolor='#F1F3EC',plot_bgcolor='#F1F3EC',
                              font_color='#46564B',margin=dict(l=10,r=15,t=15,b=25),
                              xaxis_title='Access assignments',yaxis_title=None)
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info('Load the synthetic enterprise dataset to see application access.')
    with right:
        st.markdown('#### Identity roles')
        if selected:
            df = pd.DataFrame(selected)
            fig = px.pie(df,names='role',hole=.62,
                         color_discrete_sequence=['#AFC9B2','#E4D095','#DDBAC4','#C8C2D9'])
            fig.update_layout(height=420,paper_bgcolor='#F1F3EC',font_color='#46564B',
                              margin=dict(l=10,r=10,t=15,b=20))
            st.plotly_chart(fig,use_container_width=True)

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
