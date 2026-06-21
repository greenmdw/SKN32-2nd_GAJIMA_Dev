# GAJIMA Dashboard Streamlit

Face register/login UI for the GAJIMA dashboard.

## Run

```powershell
cd outputs/dashboard_streamlit
streamlit run app.py
```

## Face Auth Flow

- Register: ID input -> duplicate check -> OpenCV face detection -> backend `/auth/face/register`
- Login: OpenCV face detection -> backend `/auth/face/login`
- Backend owns 512d embedding, L2 normalization, encryption, `face_user` write, cosine similarity, threshold decision, and `face_login_log` write.

## Backend APIs Used

- `GET /auth/face/check-id?user_id={user_id}`
- `POST /auth/face/register` multipart: `image`, `user_id`, `display_name`, `role`, `face_bbox`
- `POST /auth/face/login` multipart: `image`, `face_bbox`

`/auth/face/check-id` is required for the requested duplicate-check step, but it was not in the original 19-4 contract.
