"""
Knowledge Library page - Search, manage and integrate compliance knowledge entries
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from modules.database import NexcomplyDB
from modules.auth import AuthManager, get_current_username
from modules.theme import apply_theme

# Page configuration
st.set_page_config(
    page_title="Knowledge Library - Nexcomply",
    layout="wide"
)

# Initialize
auth = AuthManager()
db = NexcomplyDB()

# Authentication check
if not auth.is_authenticated():
    st.warning("Please login to access the Knowledge Library")
    auth.show_login_form()
    st.stop()


# Display constants
_MAX_CONTENT_PREVIEW = 1000
_MAX_TAGS_DISPLAYED = 10
_MAX_CHART_ITEMS = 20
_PAGE_SIZE = 20


@st.cache_data(show_spinner=False)
def load_kl_excel_data():
    """Load knowledge library Q&A entries from the Dummy KL Excel files."""
    kl_dir = "Dummy KL"
    answer_file = os.path.join(kl_dir, "(Answer Library Entry) Danfe Corp KL.xlsx")
    if not os.path.exists(answer_file):
        return pd.DataFrame(), None

    try:
        df = pd.read_excel(answer_file, sheet_name="AnswerLibraryEntry")
    except Exception as exc:
        return pd.DataFrame(), str(exc)

    # Keep only active (non-deleted) rows
    df = df[df["deleted_at"].isna()].copy()

    # Combine answer + details into a single content column
    df["content"] = df.apply(
        lambda r: (
            ("Answer: " + str(r["answer"]) if pd.notna(r["answer"]) and str(r["answer"]).strip() else "")
            + ("\n\n" + str(r["details"]) if pd.notna(r["details"]) and str(r["details"]).strip() else "")
        ).strip(),
        axis=1,
    )

    result = pd.DataFrame({
        "id": df["id"].astype(str),
        "title": df["question"].fillna("").astype(str),
        "category": df["category"].fillna("General").astype(str),
        "content": df["content"].astype(str),
        "tags": df["category"].fillna("").astype(str),
        "framework": "Questionnaire",
        "control_id": "",
        "created_at": pd.to_datetime(df["created_at"], errors="coerce"),
        "created_by": "Imported",
        "source": "file",
    })

    return result.reset_index(drop=True), None


def get_all_kl_entries():
    """Return combined entries from Excel files and the database."""
    frames = []
    load_errors = []

    # Load from Excel files
    file_df, file_err = load_kl_excel_data()
    if file_err:
        load_errors.append(f"Excel load error: {file_err}")
    if not file_df.empty:
        frames.append(file_df)

    # Load from database
    try:
        db_df = db.get_kl_entries()
        if not db_df.empty:
            db_df = db_df.copy()
            db_df["source"] = "database"
            db_df["id"] = db_df["id"].astype(str)
            target_cols = list(file_df.columns) if not file_df.empty else list(db_df.columns)
            # Only keep columns that exist in db_df
            target_cols = [c for c in target_cols if c in db_df.columns]
            frames.append(db_df[target_cols])
    except Exception as exc:
        load_errors.append(f"Database load error: {exc}")

    if not frames:
        return pd.DataFrame(), load_errors

    combined = pd.concat(frames, ignore_index=True)
    return combined, load_errors


# Load all entries once and cache in session state so sidebar filters work
if "kl_all_entries" not in st.session_state or "kl_load_errors" not in st.session_state:
    _entries, _errors = get_all_kl_entries()
    st.session_state.kl_all_entries = _entries
    st.session_state.kl_load_errors = _errors

all_entries = st.session_state.kl_all_entries
_load_errors = st.session_state.get("kl_load_errors", [])

# Build category list from actual data
if not all_entries.empty and "category" in all_entries.columns:
    data_categories = sorted(all_entries["category"].dropna().unique().tolist())
else:
    data_categories = []
category_options = ["All"] + data_categories

# Main content
st.title("Knowledge Library")
st.markdown("### Search, manage and integrate compliance knowledge entries")
st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "Search",
    "Add Entry",
    "Manage Entries",
    "Gap Integration"
])

# Sidebar search and filters
with st.sidebar:
    st.image("Nexcomplylogo.png", use_container_width=True)

    st.subheader("Filters")

    sidebar_search = st.text_input("Quick Search", placeholder="Search entries...", key="sidebar_search")

    sidebar_category = st.selectbox(
        "Category",
        category_options,
        key="sidebar_category"
    )

    if st.button("Clear Filters", use_container_width=True):
        st.session_state.sidebar_search = ""
        st.session_state.sidebar_category = "All"
        st.rerun()

    st.markdown("---")
    if st.button("Reload Library", use_container_width=True):
        st.cache_data.clear()
        for _key in ("kl_all_entries", "kl_load_errors"):
            if _key in st.session_state:
                del st.session_state[_key]
        st.rerun()

with tab1:
    st.subheader("Search Knowledge Library")

    # Show any load errors as warnings
    for _err in _load_errors:
        st.warning(_err)

    col1, col2 = st.columns([4, 1])

    with col1:
        search_term = st.text_input(
            "Search",
            value=sidebar_search,
            placeholder="Enter keywords to search questions, answers, or categories...",
            label_visibility="collapsed",
            key="tab1_search"
        )

    with col2:
        category_filter = st.selectbox(
            "Category",
            category_options,
            index=category_options.index(sidebar_category) if sidebar_category in category_options else 0,
            label_visibility="collapsed",
            key="tab1_category"
        )

    st.markdown("---")

    # Filter entries
    try:
        if all_entries.empty:
            st.info("No entries found in the Knowledge Library.")
        else:
            filtered = all_entries.copy()

            if category_filter != "All":
                filtered = filtered[filtered["category"] == category_filter]

            if search_term:
                mask = (
                    filtered["title"].str.contains(search_term, case=False, na=False)
                    | filtered["content"].str.contains(search_term, case=False, na=False)
                    | filtered["tags"].str.contains(search_term, case=False, na=False)
                )
                filtered = filtered[mask]

            st.success(f"Found {len(filtered):,} entries")

            # Pagination
            total_pages = max(1, (len(filtered) + _PAGE_SIZE - 1) // _PAGE_SIZE)
            page_num = st.number_input(
                f"Page (1-{total_pages})",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1,
                key="kl_page"
            )
            start = (page_num - 1) * _PAGE_SIZE
            page_df = filtered.iloc[start: start + _PAGE_SIZE]

            for _, row in page_df.iterrows():
                label = f"[{row['category']}] {str(row['title'])[:120]}"
                with st.expander(label):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown("**Question / Title:**")
                        st.write(str(row["title"]))

                        if str(row.get("content", "")).strip():
                            st.markdown("**Answer / Details:**")
                            st.write(str(row["content"])[:_MAX_CONTENT_PREVIEW])

                        if str(row.get("tags", "")).strip():
                            tags = [t.strip() for t in str(row["tags"]).split(",") if t.strip()]
                            st.markdown("**Tags:** " + " | ".join([f"`{t}`" for t in tags[:_MAX_TAGS_DISPLAYED]]))

                    with col2:
                        st.caption(f"Category: {row['category']}")
                        if str(row.get("control_id", "")).strip():
                            st.info(f"Control ID: {row['control_id']}")
                        st.caption(f"Source: {row.get('source', 'N/A')}")
                        st.caption(f"Added: {str(row.get('created_at', ''))[:10]}")

                        btn_key = f"use_{row['id']}_{start}"
                        if st.button("Use in Analysis", key=btn_key):
                            st.session_state.kl_selected_entry = row.to_dict()
                            st.success("Entry selected for analysis integration")

    except Exception as e:
        st.error(f"Error loading entries: {str(e)}")

with tab2:
    st.subheader("Add New Knowledge Library Entry")
    
    with st.form("add_kl_entry"):
        col1, col2 = st.columns(2)
        
        with col1:
            entry_title = st.text_input("Title *", placeholder="e.g., Access Control Policy - MFA Requirement")
            entry_category = st.selectbox(
                "Category *",
                ["Policy", "Control", "Procedure", "Guideline", "Framework", "Questionnaire"],
                key="add_entry_category"
            )
            entry_framework = st.selectbox(
                "Framework",
                ["ISO 27001", "SOC 2", "NIST", "GDPR", "PCI DSS", "HIPAA", "NRB", "Other", "N/A"],
                key="add_entry_framework"
            )
            entry_control_id = st.text_input("Control ID", placeholder="e.g., A.9.4.2")
        
        with col2:
            entry_tags = st.text_input(
                "Tags (comma-separated)",
                placeholder="access control, MFA, authentication"
            )
        
        entry_content = st.text_area(
            "Content *",
            height=200,
            placeholder="Enter the knowledge entry content, description, or guidance..."
        )
        
        submitted = st.form_submit_button("Add Entry", use_container_width=True, type="primary")
        
        if submitted:
            if not entry_title or not entry_content:
                st.error("Title and Content are required")
            else:
                try:
                    entry_id = db.add_kl_entry(
                        title=entry_title,
                        category=entry_category,
                        content=entry_content,
                        tags=entry_tags,
                        framework=entry_framework,
                        control_id=entry_control_id,
                        created_by=get_current_username()
                    )
                    db.log_activity(
                        get_current_username(),
                        "Knowledge Library",
                        f"Added entry: {entry_title}"
                    )
                    st.success(f"Entry added successfully! (ID: {entry_id})")
                except Exception as e:
                    st.error(f"Error adding entry: {str(e)}")

with tab3:
    st.subheader("Manage Custom Entries")
    st.markdown("Manage entries added manually via the 'Add Entry' tab.")

    try:
        db_entries = db.get_kl_entries()

        if db_entries.empty:
            st.info("No custom entries in the knowledge library yet. Add entries in the 'Add Entry' tab.")
        else:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Custom Entries", len(db_entries))
            with col2:
                frameworks = db_entries['framework'].nunique()
                st.metric("Frameworks Covered", frameworks)
            with col3:
                categories = db_entries['category'].nunique()
                st.metric("Categories", categories)

            st.markdown("---")

            # Display entries table
            display_cols = ['id', 'title', 'category', 'framework', 'control_id', 'created_at']
            display_df = db_entries[[c for c in display_cols if c in db_entries.columns]].copy()
            if 'created_at' in display_df.columns:
                display_df['created_at'] = pd.to_datetime(display_df['created_at'], errors='coerce').dt.strftime('%Y-%m-%d')
            st.dataframe(display_df, use_container_width=True)

            st.markdown("---")

            # Edit/Delete entry
            col1, col2 = st.columns([2, 1])
            entry_ids = db_entries['id'].tolist()

            with col1:
                st.subheader("Edit Entry")

                selected_id = st.selectbox(
                    "Select Entry to Edit",
                    entry_ids,
                    format_func=lambda x: db_entries[db_entries['id'] == x]['title'].iloc[0],
                    key="edit_selector"
                )

                if selected_id:
                    selected_entry = db_entries[db_entries['id'] == selected_id].iloc[0]

                    with st.form("edit_kl_entry"):
                        edit_title = st.text_input("Title", value=selected_entry['title'])
                        cat_choices = ["Policy", "Control", "Procedure", "Guideline", "Framework", "Questionnaire"]
                        edit_category = st.selectbox(
                            "Category",
                            cat_choices,
                            index=cat_choices.index(selected_entry['category'])
                            if selected_entry['category'] in cat_choices else 0,
                            key="edit_entry_category"
                        )
                        edit_framework = st.text_input("Framework", value=str(selected_entry.get('framework', '')))
                        edit_control_id = st.text_input("Control ID", value=str(selected_entry.get('control_id', '')))
                        edit_tags = st.text_input("Tags", value=str(selected_entry.get('tags', '')))
                        edit_content = st.text_area("Content", value=selected_entry['content'], height=150)

                        if st.form_submit_button("Update Entry", use_container_width=True):
                            try:
                                db.update_kl_entry(
                                    entry_id=selected_id,
                                    title=edit_title,
                                    category=edit_category,
                                    content=edit_content,
                                    tags=edit_tags,
                                    framework=edit_framework,
                                    control_id=edit_control_id
                                )
                                db.log_activity(
                                    get_current_username(),
                                    "Knowledge Library",
                                    f"Updated entry: {edit_title}"
                                )
                                st.success("Entry updated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating entry: {str(e)}")

            with col2:
                st.subheader("Delete Entry")

                del_entry_id = st.selectbox(
                    "Select Entry to Delete",
                    entry_ids,
                    format_func=lambda x: db_entries[db_entries['id'] == x]['title'].iloc[0],
                    key="delete_selector"
                )

                st.warning("This action cannot be undone.")

                if st.button("Delete Entry", type="primary", use_container_width=True):
                    try:
                        del_title = db_entries[db_entries['id'] == del_entry_id]['title'].iloc[0]
                        db.delete_kl_entry(del_entry_id)
                        db.log_activity(
                            get_current_username(),
                            "Knowledge Library",
                            f"Deleted entry: {del_title}"
                        )
                        st.success("Entry deleted!")
                        # Invalidate cache so search tab picks up the change
                        if "kl_all_entries" in st.session_state:
                            del st.session_state.kl_all_entries
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting entry: {str(e)}")

    except Exception as e:
        st.error(f"Error loading entries: {str(e)}")

with tab4:
    st.subheader("Knowledge Library - Gap Analysis Integration")
    st.markdown("Use knowledge library entries to enhance gap analysis with pre-defined controls.")

    st.markdown("---")

    if 'kl_selected_entry' in st.session_state:
        st.success("Selected Entry for Integration:")
        entry = st.session_state.kl_selected_entry

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Title:** {str(entry.get('title', ''))[:_MAX_CONTENT_PREVIEW]}")
            st.markdown(f"**Category:** {entry.get('category', 'N/A')}")
            st.markdown(f"**Framework:** {entry.get('framework', 'N/A')}")
            content_preview = str(entry.get('content', ''))[:_MAX_CONTENT_PREVIEW]
            st.markdown(f"**Content:** {content_preview}{'...' if len(str(entry.get('content', ''))) > _MAX_CONTENT_PREVIEW else ''}")

        with col2:
            if entry.get('control_id'):
                st.info(f"Control ID: {entry['control_id']}")

            if st.button("Clear Selection"):
                del st.session_state.kl_selected_entry
                st.rerun()

        st.markdown("---")
        st.info("Navigate to the Analysis page to run gap analysis. The selected entry will be available as a reference control.")
    else:
        st.info("No entry selected. Search for entries and click 'Use in Analysis' to integrate with gap analysis.")

    st.markdown("---")

    # Coverage summary from all sources
    st.subheader("Knowledge Library Coverage Summary")

    try:
        if not all_entries.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**By Framework:**")
                fw_counts = all_entries['framework'].value_counts().head(_MAX_CHART_ITEMS)
                st.bar_chart(fw_counts)

            with col2:
                st.markdown("**By Category:**")
                cat_counts = all_entries['category'].value_counts().head(_MAX_CHART_ITEMS)
                st.bar_chart(cat_counts)

            st.metric("Total Entries in Library", len(all_entries))
        else:
            st.info("No knowledge library data available.")

    except Exception as e:
        st.error(f"Error loading coverage data: {str(e)}")

# Footer
st.markdown("---")
st.markdown(f"*Page loaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
