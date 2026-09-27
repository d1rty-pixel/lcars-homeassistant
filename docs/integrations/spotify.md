# Media players (and Spotify)

Used by `player` (now playing, output devices, transport) and `library` (the media browser), and by
readouts of the player's state.

The cards use standard `media_player` features, so any player works; what a library offers depends on
the integration (its media browser's categories). Spotify needs a few extra steps and has quirks the
cards handle, described here.

## Setup (Spotify)

1. **Create a Spotify app** at <https://developer.spotify.com/dashboard>:
   - Redirect URI: `https://my.home-assistant.io/redirect/oauth`
   - APIs used: Web API
   - "Development mode" is fine for your own account. Other accounts must be added under
     *User Management* before they can log in.
2. **Add the integration** in HA: Settings → Devices & services → Add integration → **Spotify**. When
   asked for application credentials, enter any name and the app's Client ID and Client Secret, then
   log in to Spotify and approve the access.
3. The entity is named after the account (`media_player.spotify_<name>`). A pattern finds it when the
   dashboard is built, so relinking only needs a rebuild:

```yaml
- {type: player, entity: media_player.spotify_*, part: now, name: Spotify}
- type: library
  entity: media_player.spotify_*
  name: Spotify
  categories:
    - {match: current_user_playlists, label: Playlists, colour: peach, pinned: [current_user_saved_tracks]}
    - {match: current_user_saved_albums, label: Albums, colour: almond}
    - {match: current_user_followed_artists, label: Artists, colour: butterscotch}
    - {match: current_user_recently_played, label: Recent, colour: peach}
    - {match: current_user_top_tracks, label: Top tracks, colour: almond}
```

Playback control needs **Spotify Premium**. Without it, the player shows what is playing but the
buttons have no effect.

## What the cards use

| Feature | From the entity |
|---------|-----------------|
| Title, artist, album, cover | `media_title`, `media_artist`, `media_album_name`, `entity_picture` (HA's image proxy) |
| Progress bar (tap to seek) | `media_position`, `media_position_updated_at`, `media_duration`; `media_player.media_seek` |
| Transport | `media_play_pause`, `media_previous_track`, `media_next_track`, `shuffle_set`, `repeat_set` (off → all → one) |
| Volume slider (drag, sent on release) | `volume_level`; `media_player.volume_set` |
| Output devices | `source_list` / `source` (for Spotify: the Spotify Connect devices); `media_player.select_source` |
| Library | `media_player/browse_media` (WebSocket); a row plays with `media_player.play_media` |

Buttons the entity doesn't support right now (per `supported_features`) are greyed out. A library
category matches the end of a root entry's `media_content_id`; Spotify also offers
`current_user_saved_shows` and `current_user_top_artists`. **Liked songs** (`current_user_saved_tracks`)
isn't a playlist in Spotify's API, so it is pinned as the first row of Playlists and plays the whole
collection as one context.

## Spotify's quirks

- **Idle Spotify** (nothing played recently): without an active Spotify Connect device, HA's Spotify
  entity reports only "select source" and rejects play_media, play/pause and browsing. **Play**, or a
  library tap, first wakes an output device (the one last used in this browser, else the first listed)
  with `select_source`, which wakes it paused; the cards wait for the full feature set, then play. The
  library shows the last list it loaded per category meanwhile, or a **Connect** row.
- **Refused commands**: Spotify rejects some commands in some contexts (e.g. Repeat: 403 "Restriction
  violated"; HA doesn't expose Spotify's "disallows"). The button flashes red and the status shows
  "Spotify refused · Repeat" (the component's `name`) for a few seconds.
- **Output devices** are the devices Spotify currently lists; one that is asleep or has Spotify closed
  disappears until Spotify is opened on it again.
