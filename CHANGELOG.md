# Changelog

## [v1.0.0] - 2026-05-20
### ✨ Added
- Multi-step form with FSM state management
- Telegram group + Google Sheets auto-sync
- Dynamic access control (`/allow`, `/remove`, `/users`)
- Multi-admin support & role-based routing
- `=HYPERLINK()` formulas for clickable profiles
- `Asia/Tashkent` timezone normalization
- Full navigation (back/cancel/edit preview)

### 🐛 Fixed
- Pydantic frozen model error on `InputMedia`
- Removed invalid `bot.get_message()` calls
- Webhook DNS loop & startup crashesCHANGELOG
- Circular imports & router architecture
- Sync loop rate limits & chunked validation

### 📚 Docs
- Uzbek admin guide & troubleshooting manual
- `.env.example` & systemd service template