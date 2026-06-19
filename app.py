from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
STYLES_DIR = BASE_DIR / "styles"


MODEL_METRIC_COLUMNS = [
    "accuracy",
    "precision",
    "recall",
    "f1_score",
    "roc_auc",
    "pr_auc",
]


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_css(path: Path) -> None:
    css = load_text(path)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def go_to(page_name: str) -> None:
    st.session_state.page = page_name


def init_session_state() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "landing"

    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False


def get_model_results() -> list[dict]:
    """Backend 연결 전까지 ML 모델 3개의 결과를 직접 받는 임시 진입점입니다."""
    return [
        {
            "model_name": "churn-model_1",
            "accuracy": 0.914,
            "precision": 0.887,
            "recall": 0.842,
            "f1_score": 0.864,
            "roc_auc": 0.931,
            "pr_auc": 0.902,
            "confusion_matrix": {"TP": 128, "TN": 746, "FP": 31, "FN": 24},
        },
        {
            "model_name": "churn-model_2",
            "accuracy": 0.902,
            "precision": 0.861,
            "recall": 0.875,
            "f1_score": 0.868,
            "roc_auc": 0.924,
            "pr_auc": 0.894,
            "confusion_matrix": {"TP": 133, "TN": 730, "FP": 47, "FN": 19},
        },
        {
            "model_name": "churn-model_3",
            "accuracy": 0.921,
            "precision": 0.901,
            "recall": 0.856,
            "f1_score": 0.878,
            "roc_auc": 0.938,
            "pr_auc": 0.911,
            "confusion_matrix": {"TP": 130, "TN": 751, "FP": 26, "FN": 22},
        },
    ]


def format_score(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def build_model_metrics_table(model_results: list[dict]) -> list[dict]:
    table_rows = []

    for result in model_results:
        row = {"model_name": result.get("model_name", "-")}
        for column in MODEL_METRIC_COLUMNS:
            row[column] = format_score(result.get(column))
        table_rows.append(row)

    return table_rows


def render_model_metrics_table(model_results: list[dict]) -> None:
    st.subheader("Model Performance")
    st.dataframe(
        build_model_metrics_table(model_results),
        use_container_width=True,
        hide_index=True,
        column_config={
            "model_name": st.column_config.TextColumn("Model"),
            "accuracy": st.column_config.TextColumn("Accuracy"),
            "precision": st.column_config.TextColumn("Precision"),
            "recall": st.column_config.TextColumn("Recall"),
            "f1_score": st.column_config.TextColumn("F1 Score"),
            "roc_auc": st.column_config.TextColumn("ROC-AUC"),
            "pr_auc": st.column_config.TextColumn("PR-AUC"),
        },
    )


def render_confusion_matrix(model_results: list[dict]) -> None:
    st.subheader("Confusion Matrix")

    model_names = [result["model_name"] for result in model_results]
    selected_model_name = st.selectbox("Model", model_names)
    selected_result = next(result for result in model_results if result["model_name"] == selected_model_name)
    confusion_matrix = selected_result.get("confusion_matrix", {})

    tp = confusion_matrix.get("TP", 0)
    tn = confusion_matrix.get("TN", 0)
    fp = confusion_matrix.get("FP", 0)
    fn = confusion_matrix.get("FN", 0)

    matrix_rows = [
        {
            "Actual": "Non-Churn",
            "Predicted Non-Churn": tn,
            "Predicted Churn": fp,
        },
        {
            "Actual": "Churn",
            "Predicted Non-Churn": fn,
            "Predicted Churn": tp,
        },
    ]

    st.dataframe(matrix_rows, use_container_width=True, hide_index=True)

    col_tp, col_tn, col_fp, col_fn = st.columns(4)
    col_tp.metric("TP", tp)
    col_tn.metric("TN", tn)
    col_fp.metric("FP", fp)
    col_fn.metric("FN", fn)


def render_landing_page() -> None:
    logo_svg = load_text(ASSETS_DIR / "logo.svg")

    st.markdown(f'<div class="logo">{logo_svg}</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="brand-title">Anchor</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="brand-sub">실시간 고객 이탈 분석 시스템</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="button-wrap">', unsafe_allow_html=True)
    if st.button("얼굴 로그인", use_container_width=True, key="btn_face"):
        go_to("login")
        st.rerun()
    if st.button("회원가입", use_container_width=True, key="btn_register"):
        go_to("register")
        st.rerun()
    if st.button("비밀번호 찾기", use_container_width=True, key="btn_reset"):
        go_to("password_reset")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="foot">Powered by Anchor AI</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_login_page() -> None:
    st.title("Login")
    st.caption("얼굴 로그인 기능이 연결될 페이지입니다.")

    if st.button("로그인 완료 테스트"):
        st.session_state.is_logged_in = True
        go_to("dashboard")
        st.rerun()

    if st.button("랜딩 페이지로 돌아가기"):
        go_to("landing")
        st.rerun()


def render_dashboard_page() -> None:
    if not st.session_state.is_logged_in:
        go_to("login")
        st.rerun()

    model_results = get_model_results()

    st.title("Dashboard")
    st.caption("이진 분류 모델 3개의 고객 이탈 예측 성능을 비교합니다.")

    render_model_metrics_table(model_results)
    st.divider()
    render_confusion_matrix(model_results)

    if st.button("로그아웃"):
        st.session_state.is_logged_in = False
        go_to("landing")
        st.rerun()


def render_placeholder_page(title: str, description: str) -> None:
    st.title(title)
    st.caption(description)

    if st.button("랜딩 페이지로 돌아가기"):
        go_to("landing")
        st.rerun()


def render_current_page() -> None:
    page = st.session_state.page

    if page == "landing":
        render_landing_page()
    elif page == "login":
        render_login_page()
    elif page == "dashboard":
        render_dashboard_page()
    elif page == "register":
        render_placeholder_page("Register", "회원가입 기능이 연결될 페이지입니다.")
    elif page == "password_reset":
        render_placeholder_page("Password Reset", "비밀번호 찾기 기능이 연결될 페이지입니다.")
    else:
        go_to("landing")
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="Anchor", page_icon="A", layout="centered")
    load_css(STYLES_DIR / "main.css")
    init_session_state()
    render_current_page()


if __name__ == "__main__":
    main()
