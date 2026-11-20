# Bites customer app: final design

The customer-only app for Bites by Batore. The admin tools (Operations) stay in the existing web app and are not part of this design.

- Live prototype (private, owner only): https://claude.ai/artifact/QLxeEEZ8mWUXA37SGFb5s7 (opens on the connected app)
- Navigation flowchart: [navigation-flowchart.png](navigation-flowchart.png) (source: [navigation-flowchart.html](navigation-flowchart.html))
- Screens: [screens/](screens/). `App.dc.html` is the connected, final prototype. The other `.dc.html` files are earlier single-screen drafts kept for reference.
- Logos: [brand/](brand/) (`bites-star.svg`, `batore-wordmark.svg`, recolourable with CSS masks)

All places, prices, plans and names in the prototype are sample content.

## Look and feel

| Colour | Hex | Use |
|---|---|---|
| Espresso | `#1F140C` | Dark screens, primary buttons, tab bar |
| Cocoa | `#4A2E18` | Chips on dark |
| Caramel | `#8A5A2B` | Secondary text |
| Gold | `#C8962E` | Dots, lines, borders |
| Turmeric | `#F5C842` | Whatever is selected, highlights |
| Cream | `#FBF2DC` | Light screens |
| Leaf / Pistachio | `#2E6B3E` / `#9BBF65` | Only "Open", "Added", "Coming up" and the tagline |

- Type: Plus Jakarta Sans; Fraunces italic for small accents ("vibe", "tonight.", the name on Home, the tagline).
- Dark screens: Welcome, Sign in, Making your plan, Share a find. Everything else is cream.
- Motion is dots only: the Welcome star, the dot floor and its reflection, dotted roads, the dot clock loader, dot sliders for budget, time and ratings. Nothing auto-rotates. Everything respects Reduce Motion.
- Welcome hero: the Batore site's dot-star engine (`lib/site-engine.js`, DotStar), in the Bites palette: forms from scattered dots, faces forward with a slight tilt, tilts toward the finger, dots move away from touch, dot floor with a rippled reflection, no spotlight.
- No visible scroll bars. Text is sentence case, plain words, units written as "per person", "45 min", "1 hr 30 min", "From 8 pm".

## Screens and navigation

Tab bar (Home, Explore, Saved) shows only on those three screens; every other page has Back.

| Page | Goes to |
|---|---|
| Welcome | Let's go out → Sign in |
| Sign in | Google / email link / Not now → Home · Terms, Privacy → Privacy and terms |
| Home | Area chip → Area sheet · Avatar → My taste · Plan something → Set the vibe · Quick chips → Making your plan · Coming up → Plan detail · Instagram card → Share a find |
| Set the vibe | Mood, who's coming, leaving time (Now, 6, 7, 8 pm + clock for any time), total time (1–6 hrs), budget (per person or total), interests → Make my plan |
| Making your plan | After about 4 s, or See plans → Your plans |
| Your plans | Only plans within budget and time · Edit / Change filters → Set the vibe · Choose this plan → Plan detail (and saves it) |
| Plan detail | Save · lock a stop · swap last stop · tap a stop → Place |
| Explore | Search · Food / Things to do · Change → Area sheet · row → Place |
| Place | Save · Directions → Google Maps · Plan around this → Set the vibe |
| Saved | Plans / Places · tap → Plan detail or Place |
| My taste | Food, spice, cuisines · Places you've been · Dish diary · Download my data · Privacy and terms · Sign out → Welcome · Delete my account → confirmation sheet |
| Places you've been | Rate with dots · remove · Log a visit · tap → Place |
| Dish diary | All / Loved / Not for me · rate with dots · Add a dish |
| Share a find | Paste a link and Send, or upload a video → listed as Checking / Added / Couldn't confirm |
| Area sheet | Use my current location or pick an area → updates Home and Explore |
| Delete account sheet | Keep my account, or Delete → data wiped, back to Welcome |

## Before production

- Wire every screen to the real backend (`/api/plans`, places, saved, taste, sources) and to real sign-in (Supabase Google and email link).
- Area sheet, search and plan filters are simulated in the prototype; real results must come from the API.
- Privacy and Terms copy is a plain-language draft: it needs legal review and contact details.
- Replace the dotted photo placeholder on Place with real photos when available.
- The Instagram gradient on the Home card is the one intentional exception to the palette.
