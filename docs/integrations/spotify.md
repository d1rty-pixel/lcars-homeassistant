# Spotify

Used by **Media → Player**: the "Now playing" frame (`custom:lcars-player`) and the "Library" frame
(`custom:lcars-library`), plus the Audio and Output readouts in the header.

## Setup

1. **Create a Spotify app** at <https://developer.spotify.com/dashboard>:
   - Redirect URI: `https://my.home-assistant.io/redirect/oauth`
   - APIs used: Web API
   - "Development mode" is fine for your own account. Other accounts must be added under
     *User Management* before they can log in.
2. **Add the integration** in HA: Settings → Devices & services → Add integration → **Spotify**.
   When asked for application credentials, enter any name and the app's Client ID and Client Secret
   (Spotify dashboard → your app → Settings → *View client secret*). Then log in to Spotify and
   approve the access.
3. **Rebuild the dashboard** (`python3 tools/deploy.py`). The generator picks the first
   `media_player.spotify*` entity at build time (`spotify_entity()`). The entity is named after the
   Spotify account, e.g. `media_player.spotify_jane`, so a rebuild is needed after linking or
   relinking.

Playback control needs **Spotify Premium**. Without it, the player shows what is playing but the
buttons have no effect.

## What the cards use

| Feature | From the entity |
|---------|-----------------|
| Title, artist, album, cover | `media_title`, `media_artist`, `media_album_name`, `entity_picture` (HA's image proxy) |
| Progress bar (tap to seek) | `media_position`, `media_position_updated_at`, `media_duration`; `media_player.media_seek` |
| Transport pillar | `media_play_pause`, `media_previous_track`, `media_next_track`, `shuffle_set`, `repeat_set` (off → all → one) |
| Volume slider (drag, sent on release) | `volume_level`; `media_player.volume_set` |
| Output pills | `source_list` / `source` (Spotify Connect devices); `media_player.select_source` |
| Library | `media_player/browse_media` (WebSocket); a row plays with `media_player.play_media` |

Buttons the entity doesn't support right now (per `supported_features`) are greyed out.

The library categories are matched against the end of the browse root's `media_content_id`
(`LIBRARY` in the generator): `current_user_playlists`, `current_user_saved_albums`,
`current_user_followed_artists`, `current_user_recently_played`, `current_user_top_tracks`. The
integration also offers `current_user_saved_shows` and `current_user_top_artists`, so you can add
those.

**Liked songs** (`current_user_saved_tracks`) isn't a playlist in Spotify's API, so it is pinned as the
first row of Playlists (`LIBRARY_PINNED`), marked ♥. Tapping it plays the whole collection as one
context, so shuffle and next work across all liked songs.

## Notes and limitations

- **Idle Spotify (nothing played recently)**: without an active Spotify Connect device, HA's Spotify
  entity reports only "select source" (`supported_features: 2048`). HA then rejects `play_media`,
  play/pause and media browsing. The cards handle it like this:
  - **Play**, or tapping a library entry, first *wakes* an output device: the one last used in this
    browser, else the first listed. That is a `select_source` (Spotify transfer playback without
    `play`, so the device wakes up paused). The cards wait for HA to report the full feature set, then
    resume or play.
  - The library shows the last list it loaded for each category (kept in the browser's localStorage).
    Without one, it shows a **Connect** row that wakes the device and loads the library.
  - Play resumes whatever Spotify played last on that device. If there is nothing to resume, start
    something from the library.
- **Output devices** are the Spotify Connect devices that Spotify currently lists. A device that is
  asleep or has Spotify closed disappears until Spotify is opened on it again. "No output devices"
  means none is active right now.
- Device names come from Spotify as they are. Web players often show up with generated names.
- The library shows as many entries as the integration returns per category. It doesn't page through
  Spotify's API beyond that.
- Other media players work too: the cards only use standard `media_player` features. Point `SPOTIFY`
  at another entity. Its library categories will differ, so adjust `LIBRARY`.
