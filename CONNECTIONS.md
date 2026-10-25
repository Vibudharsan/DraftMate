# Calendar and communications

## Working locally

- Month calendar and day agenda in Asia/Kolkata, previous/next month, today, optional selected-case filter.
- Create/edit local events, case association, location, notes and reminder lead time, with confirmation before saving/deleting.
- Local reminders are in-app notices while this page is open. They are not background OS notifications or Google reminders.
- Fictional inbox examples, original plain text and opening-sentence extractive reports. Reports are not LLM-generated legal interpretations.
- Local email/WhatsApp/SMS draft composer, per-draft case association, reply context, saved drafts, and exact-content review.
- WhatsApp/SMS draft links open the appropriate app. Sending must be completed there; the site cannot read responses or confirm delivery.

## Google connection setup

The app's own Google connection is separate from any Google connector in ChatGPT.

1. In Google Cloud, enable the Gmail API and Google Calendar API for your project.
2. Configure the OAuth consent screen and, during testing, add the intended Google account as a test user.
3. Create an OAuth client of type **Web application**. Add `http://127.0.0.1:4174` as an authorised JavaScript origin. Add your exact deployed HTTPS origin separately if deploying later.
4. Open DraftMate → Connections → Configure client ID. Enter the client ID ending in `.apps.googleusercontent.com`.
5. Click Connect Google Calendar or Connect Gmail and complete Google's consent flow yourself.

Only the public client ID is persisted. Do not put a client secret, API access token or Google password into this app. Google Identity Services loads when a connection is requested. Access tokens stay in JavaScript memory, expire, and are cleared on reload/disconnection. No refresh token or unattended server sync is implemented.

Scopes:

- Calendar: `https://www.googleapis.com/auth/calendar.events`.
- Gmail: `https://www.googleapis.com/auth/gmail.readonly` and `https://www.googleapis.com/auth/gmail.send`.

Calendar code reads primary-calendar events for the selected month, paginates with a 2,500-event ceiling, and can create, edit and delete permitted events through the Google API. Shared, recurring-instance and special events are read-only in this UI. Calendar writes have no attendees. Google reminders use popup overrides; delivery depends on Google notification settings. ETags are used for existing event writes.

Gmail code reads inbox metadata in pages of 20, fetches the plain-text body on selection, supports original references and thread ID when replying, and sends only from the explicit reviewed-send action. The connected sender address is shown before sending. No attachments, HTML rendering, Gmail-draft synchronisation or cross-channel inbound aggregation are implemented. Optional one-minute polling runs only while the communications page is visible and the user has enabled it. Loaded mail remains in memory; user-saved reply drafts and case associations persist locally.

Before public release, complete Google's applicable OAuth verification and privacy/data-handling requirements. Gmail reading uses restricted scopes. This local prototype has not completed public app verification.

## WhatsApp and SMS

Incoming WhatsApp Business integration needs a Meta app, authorised business phone number, server-side credentials and a public HTTPS webhook with signature verification. These are not configured or implemented. Personal WhatsApp history is not exposed by the Business API integration described here.

A web page cannot simply read the user's phone SMS inbox. A provider-owned SMS number/webhook or a future authorised Android integration would be needed. The current SMS feature is compose-and-handoff only.

## Validation and limitations

Tested local event creation/editing/persistence, local reply-draft persistence, disconnected send gating and responsive UI. `node test_connections.cjs` checks Unicode MIME encoding, reply headers, rejection of header injection, India-time date boundaries, reminder payloads and extractive reports. Real OAuth, Calendar writes and Gmail sends have not been exercised because no Google client ID/account has been configured. No real messages were read or sent during implementation.

If a network error occurs during a send or event creation, check the provider before retrying; a response can be lost after a provider accepts the request.

## Official references

- https://developers.google.com/identity/oauth2/web/guides/use-token-model
- https://developers.google.com/workspace/calendar/api/v3/reference/events/insert
- https://developers.google.com/workspace/gmail/api/auth/scopes
- https://developers.google.com/workspace/gmail/api/guides/sending
- https://whatsappbusiness.com/developers/developer-hub/
