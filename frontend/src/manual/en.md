# Manual

Release Radar holds the office's English press releases and their numbers. The first sections are the everyday tasks; the rest of the page explains each part. Everything saves by itself.

## Add a release

On **Data**, paste a DOI or type a title in the top row of the grid and press Enter. With a DOI, Release Radar fills in the paper's journal, title, publication date and authors, and the release shows *No title yet* until you type its own title. Everything else can follow, and adding several in a row is just doing this again.

- A new release stays at the top until you change the view, even if your filters would hide it.
- It gets its code, such as `AY2026-12`, when its release date is first entered. Codes can't be edited, and a code stays the same even if the date moves to another academic year.
- It starts as a **Peer-reviewed publication** (see *Set the release type*). You are its writer.
- The paper's **Publication date** is the column right after the DOI. If Crossref knows only the month, it stays empty: type it in.
- Paste the **DOI**, the **EurekAlert link** and the **Website link** into their cells. A DOI can be bare (`10.1038/…`) or a link (`https://doi.org/10.1038/…`): Release Radar keeps the DOI either way. A saved link shows as **✓ ↗**: click the mark to open the page in a new tab, or click beside it to select the cell, for example to paste a corrected link over it.

## Fill in day-28 numbers

**Due now**, at the top of **Mine**, lists the numbers waiting for you and those due in the next three days. Type a number and press Enter, and the next one is ready. Choose **N/A** if a number doesn't apply. Nothing here is ever late: an item simply waits until you get to it.

In the grid, a tinted cell is due and empty. Click it and type the number; Enter saves it and moves down, so a column fills quickly. **N/A** on grey means the number can't exist for this release, such as Altmetric without a DOI. A plain empty cell isn't due yet. Type `-` or `N/A` to mark a number as not applicable, and press Delete to clear it.

A day-0 Altmetric score shows **0 inferred** when the paper was published on or after the release date: it can have had no attention before the release, so nobody needs to look it up. It no longer asks to be filled in. Typing a number replaces it, and deleting that number brings the inferred 0 back.

## Paste a column

Copy cells from a spreadsheet or a web page, such as a column of views from the EurekAlert portal. In the grid, select the first cell to fill and press Cmd+V (Ctrl+V on Windows). Each line fills the next row down, and each cell is checked on its own, so one bad value costs only that cell. A message says how it went, with **Undo** for the whole paste. Thousands separators such as `1,234` are fine. If you select a range and paste one value, it fills the range.

## Set the release type

Each release has a type, after EurekAlert's categories: most are **Peer-reviewed publication**, and some are a **Feature story**, a **Business announcement**, or **Reports and proceedings** (such as a conference presentation). Analysis will keep the types apart, so set the right one.

New releases start as Peer-reviewed publication, or as whatever an admin chose in Settings. To change it, select the **Release type** cell and type the type's name or a word of it, such as `feature`, then press Enter; or choose it in the full record. Above the grid, **Release type** shows one type at a time, or the releases that have none.

## Export for a report

**Export** downloads the releases shown, with your filters and in your order, or everything. Choose Excel or CSV, and English or Japanese: headings and list values follow the language, and titles and notes stay as written.

Each release is one row, with a column per number: the number, **N/A** if it can't exist, or empty if it hasn't been recorded or isn't due yet. Whatever can be a number is one, so the file needs no converting: the academic year is `2025`, and a yes-or-no column such as **Embargoed** holds `1` for yes and `0` for no. The release type and the researcher's gender have columns of their own. A colleague's own field has their name in brackets. The Excel file also has sheets with the units and fields, and a **Read me** sheet explaining all this.

The file contains personal data, such as researchers' names. Keep it within the office, and delete copies you no longer need.

## The Data page

**Mine** shows the releases you write, and **All** shows everyone's. You can fill in any of them. Once you have releases of your own, Release Radar opens on **Mine**; until then it opens on **All**.

### Work in the grid

The grid works like a spreadsheet, and the keyboard reaches everything.

- Click a cell to select it, or press Tab to reach the grid and arrive on its first cell. Arrow keys, Home and End move around. Hold Shift to select a range, or drag across cells.
- Type to replace a cell, or press Enter or F2 to change it. Enter saves and moves down, Tab saves and moves right, and Esc goes back. A box changes with the space bar.
- Cmd/Ctrl+Enter on a DOI or link cell opens its page in a new tab.
- Cmd/Ctrl+Z undoes your last edit, or your last paste as a whole, cells that couldn't be saved included.
- Esc lets go of the selected cell, so nothing is pasted over by mistake. Clicking into the new-release row does the same.
- **Researcher gender** sits next to the researcher. Type female, male or other, or just `f`, `m`, `女性`, `男性` and the like; leave it empty if it isn't recorded. It belongs to the researcher, so it changes on all of their releases.

If something can't be saved, the cell turns pink and keeps what you typed, and selecting it says why: press Enter or Backspace to correct it, or Esc to go back to what was there. Backspace takes off the last character, so a slip such as 31 for 30 needs one key, not the whole date again. Nothing else is held up.

If a colleague changed the same cell a moment before you, the cell says what they entered: choose **Keep mine** or **Use theirs**.

### The full record

Double-click any cell of a release, or press Shift+Enter, to open its full record beside the grid. On a phone or tablet, a tap opens it. The record shows every field, the paper's details, all the numbers with their notes, the researcher's feedback, and the history of who changed what. **Open ↗** beside the DOI and the links opens their page. To remove a release, use the button at the bottom. You can undo that straight away, and its code stays taken.

### Choose your columns

**Columns** chooses what the grid shows. By default it shows what analysis tells releases apart by, so it gets filled in; details such as the paper's title and authors are in the full record. Release Radar remembers your choice.

### Find and sort releases

Above the grid, type in the search box to find words in titles, researchers' names, DOIs, codes, journals and notes. Every word you type must appear somewhere. Next to it, choose an academic year, a field, a release type, a unit, a writer (in **All**) or a researcher, one click each. **Clear filters** shows everything again.

Click a column's heading to sort by it, again to reverse, and a third time to go back to newest first. With the keyboard, press the up arrow in the first row to reach the headings, move along them with the arrow keys, and press Enter to sort; the down arrow goes back to the rows. Rows stay where they are while you work on them, even if you change the value they're sorted by.

What you choose is kept in the page's address, so you can bookmark a view, such as one unit's releases this year, or send the link to a colleague.

## The Writers page

**Writers** counts each writer's releases in each month of an academic year, by release date, with a total for every writer and every month. Choose the year at the top, or **All years** to see one column per academic year instead of per month. Everyone in the writers list has a row, and so does anyone who wrote that year and has left since. Releases without a writer have a row of their own. A release without a release date is counted once it has one.

The page counts releases only, on purpose: how a release does depends mostly on its topic, not on who wrote it. The export on the Data page has every release with its writer, if you need more.

Click a name to see that writer's releases of the year on the Data page. **Export** downloads the table as Excel or CSV.

## My fields

Numbers you track for yourself, such as clicks on your own links, go here. Open the menu with your name and choose **My fields**, then add a field. Set **Due at** to get a reminder at that checkpoint. Colleagues can see your fields next to your name, and only you can change them.

## Researchers

Editors find **Researchers** in the top navigation, and admins find it under **Settings**. Search by name or identifier. Changes save as soon as you leave a field.

Two different people can share a name, so a name alone never links a release to a record. A record with a namesake shows a small label, **Others with this name**, which finds them when clicked. Tick **Same name only** to see them all. The unit, identifiers and **Notes** tell them apart, so write something in **Notes** when nothing else does, such as a lab or a topic.

To combine two records of the same person, choose **Merge** on the record you want to retire, search for the one to keep and choose **Keep this one**. Its releases move across, and any gaps on the record you keep are filled in.

If that was a mistake, choose **Undo** straight away. Later on, choose **Split** on the record you kept, and then **Undo merge**: the merged record comes back with its releases.

If one record covers two people, choose **Split**, tick the releases of the other person and choose where they go: a new record, which starts with the same name, or one that already exists.

## Your account

### Signing in

Sign in with your email address and password. The first time, you'll be asked to replace your temporary password with one of your own. It needs at least 10 characters.

You stay signed in through the working day. To sign out, open the menu with your name at the top right and choose **Sign out**.

### Forgot your password?

On the sign-in page, choose **Forgot your password?** and enter your email address. You'll receive a link that works once, for one hour. If this installation can't send email yet, the page tells you, and an administrator can reset your password.

### Changing your password

Open the menu with your name at the top right and choose **Change password**. Other devices where you are signed in will be signed out.

### Switching language

Use the button next to your name at the top right to switch between English and Japanese. Release Radar remembers your choice.

## Settings for admins

**Settings** is only visible to admins, and every section works without changing anything. Changes save themselves when you leave a field. If a colleague changed the same field a moment earlier, you see what they entered and choose which to keep.

- **Institution:** names, time zone, the month the academic year starts, your news website, and where people land after signing in.
- **Users:** invite people and set their role. To remove someone, switch off **Active**: their name stays in the history. If they tracked personal fields, pass those on or make them institution fields here.
- **Lists:** units, fields, writers, release types and vocabularies. To retire an entry, switch off **Active**. Each list can be exported to CSV, edited in a spreadsheet and imported again. An import shows what it would do before anything changes. A column you leave out of the file stays as it is. If a cell can't be used, the import names its row and column and skips only that cell.
- **Release types:** EurekAlert's eleven categories, in the order the menus show them. Rename, reorder or switch off any, or add your own. **New releases start as** sets the type new and imported releases get; choose **No type** to have people choose every time.
- **Form:** rename, hide, require or reorder the fields on a release, and add your own.
- **Checkpoints & reminders:** when numbers are collected and which numbers those are. A checkpoint can fall before the release date: use a negative number, so −3 is three days before. Choose whether its reminder comes at the start of that day or the day before. The reminder emails themselves arrive in a later phase.
- **Integrations:** Google Analytics, for website views. See *Connect Google Analytics* below.
- **Data:** backups, a full copy of your data, what the automatic jobs have been doing, and the import of the old workbook.

### Import the old workbook

In **Settings → Data**, choose the press-release workbook and the intake workbook, and choose whose the workbook's personal fields are. **Check** changes nothing: it shows what an import would do and offers a report to download, in Markdown or CSV, listing everything worth a look: names that couldn't be settled, numbers that weren't numbers, every dash, codes used twice. Read it, fix the workbook if you like, and check again. **Import** then does exactly what was checked.

Importing again is safe. Each release is found by its code and updated; an empty cell never empties anything, and a researcher chosen in Release Radar since stays. Units, fields and writers are only added, never changed: Settings looks after them.

**Only fill what is empty** is for the weeks when the team still enters releases and day-28 numbers in Excel. With it ticked, releases already in Release Radar get only what is empty or missing there; nothing already there changes, not even a value the workbook has differently (a corrected DOI stays corrected). New codes come in full. The report lists every cell it filled and every difference it left alone.

Every check and import is listed under the import, with its report to download again, so what still needs correcting can be found later. A writer's name the import doesn't know leaves the release without a writer: on the Data page, choose **No writer yet** in the writer filter to find them, and pick the writer in the grid.

## Connect Google Analytics

*For admins.* Website views come from Google Analytics: for each release whose page is on your news website, the views over its first 28 days. Release Radar fetches them by itself once a release's 28 days and two days of Google's processing have passed. You connect it once. Create the Google Cloud project under an account the office keeps, so it outlives any one person's account.

In Google Cloud and Google Analytics:

1. At console.cloud.google.com, choose or create a project, for example *release-radar*. No billing account is needed: Google does not charge for this. To share it, add a colleague as a second Owner (IAM & Admin → IAM → Grant access).
2. APIs & Services → Library → **Google Analytics Data API** → Enable.
3. IAM & Admin → Service accounts → Create service account, for example *release-radar-ga4*. It needs no roles.
4. Open it → Keys → Add key → Create new key → JSON. Your browser downloads one file: that file is the key. If Google refuses because an organisation policy disables keys, ask whoever runs that organisation.
5. Google Analytics → Admin → your news site's property → Property access management → + → Add users: the service account's address (it ends in gserviceaccount.com), role **Viewer**.
6. Admin → Property details: note the **property ID**. It is digits only; the code starting with G- is something else.

Then in **Settings → Integrations**:

7. Choose the JSON file and enter the property ID. Click **Test connection**: it reads yesterday's page views on your news website and says in plain words what is wrong, if anything. Then keep the file in the password manager and delete the downloaded copy.
8. Click **Fetch now**. The first fetch collects every release since the new website went live. After that, Release Radar fetches by itself every day after the nightly backup, and a day the computer was off costs nothing.

To check a number, open Google Analytics → Reports → Engagement → Pages and screens for the same 28 days and look up the page. A number typed into a release's record always counts instead, and fetching never changes it. When a release's page address or release date changes, its fetched number is cleared and fetched again. Releases whose 28 days have passed but which have no website views are listed under Integrations: usually the page address in the record needs a look.

## Import researcher feedback

*For admins.* The researchers' answers to the feedback survey come from Microsoft Forms until Release Radar has its own survey page. In Forms, open the survey → **Responses** → **Open results in Excel**, and save the file. Then in **Settings → Data**, under *Import researcher feedback*, choose it and click **Check**.

The check changes nothing. Its report says which column was read as what (the inquiries question is headed just "1" in the export, so it is recognised by its answers), how each response was linked to its release by the press release ID (`AY2025-011` is read as AY2025-11, and an EurekAlert link finds its release), and what is worth a look: an ID no release has, an answer written in "Other", a response with all three statements at "Strongly disagree". Four early responses used the scale the wrong way round, and the import corrects exactly those four; the response's history shows the file's answer and the correction. A new response like that is only listed, for you to decide. Then click **Import**.

Importing a newer export later is safe: each response is found again by the export's Id, so only new ones are added and imported ones stay as they are. The answers appear in each release's record under *Researcher feedback*, with the researcher's name. Names stay in the record: summary pages for researchers never show them.
