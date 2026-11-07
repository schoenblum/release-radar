# Manual

Release Radar is being built step by step. This page grows with it.

## Signing in

Sign in with your email address and password. The first time, you'll be asked to replace your temporary password with one of your own. It needs at least 10 characters.

You stay signed in through the working day. To sign out, open the menu with your name at the top right and choose **Sign out**.

## Forgot your password?

On the sign-in page, choose **Forgot your password?** and enter your email address. You'll receive a link that works once, for one hour. If this installation can't send email yet, the page tells you, and an administrator can reset your password.

## Changing your password

Open the menu with your name at the top right and choose **Change password**. Other devices where you are signed in will be signed out.

## Switching language

Use the button next to your name at the top right to switch between English and Japanese. Release Radar remembers your choice.

## The Data page

**Data** is where releases live. **Mine** shows the releases you write, and **All** shows everyone's. You can fill in any of them. Once you have releases of your own, Release Radar opens on **Mine**; until then it opens on **All**.

### Add a release

Paste a DOI or type a title in the top row and press Enter. With a DOI, Release Radar fills in the paper's journal, title, publication date and authors, and the release shows *No title yet* until you type its own title. Everything else can follow, and adding several in a row is just doing this again. A new release stays at the top until you change the view, even if your filters would hide it. A release gets its code when its release date is first entered.

The paper's details are in the full record, under **Paper**. If Crossref knows only the month a paper came out, the publication date stays empty, so type it there. You can also show **Publication date** as a column.

### Fill in the numbers

**Due now**, at the top of **Mine**, lists what is waiting for you and what comes up in the next three days. Type a number and press Enter, and the next one is ready. Choose **N/A** if it doesn't apply. Nothing here is ever late: items simply wait until you get to them.

### Work in the grid

The grid works like a spreadsheet, and everything saves by itself.

- Select a cell and type to replace it, or press Enter to change it. Enter saves and moves down, Tab saves and moves right, and Esc goes back.
- Arrow keys move around. Hold Shift to select a range, or drag across cells.
- Type `-` or `N/A` in a number cell to mark it as not applicable, and press Delete to clear it.
- Cmd/Ctrl+Z undoes your last edit, or your last paste as a whole, cells that couldn't be saved included.
- Esc lets go of the selected cell, so nothing is pasted over by mistake. Clicking into the new-release row does the same.

A tinted cell is due and empty. **N/A** on grey means the number can't exist for this release, such as Altmetric without a DOI. A plain empty cell is simply not due yet.

If something can't be saved, the cell turns pink and keeps what you typed, and selecting it says why: press Enter to change it, or Esc to go back to what was there. Nothing else is held up.

### Paste a column

Copy cells from a spreadsheet or a web page, select the first cell to fill, and press Cmd/Ctrl+V. If you select a range and paste one value, it fills the range. Each cell is checked on its own, so one bad value costs only that cell, and a message says how it went. Thousands separators such as `1,234` are fine.

### The full record

Click a title, or press Shift+Enter on a row, to open its full record beside the grid: every field, the paper's details, all the numbers with their notes, and the history of who changed what. To remove a release, use the button at the bottom. You can undo that straight away, and its code stays taken.

### Choose your columns

**Columns** chooses what the grid shows. Release Radar remembers your choice.

### Find releases

Above the grid, type in the search box to find words in titles, researchers' names, DOIs, codes, journals and notes. Every word you type must appear somewhere. Next to it, choose an academic year, a field, a unit, a writer (in **All**) or a researcher, one click each. **Clear filters** shows everything again.

Click a column's heading to sort by it, again to reverse, and a third time to go back to newest first. Rows stay where they are while you work on them, even if you change the value they're sorted by.

What you choose is kept in the page's address, so you can bookmark a view, such as one unit's releases this year, or send the link to a colleague.

### Export for a report

**Export** downloads the releases shown, with your filters and in your order, or everything. Choose Excel or CSV, and English or Japanese: headings and list values follow the language, and titles and notes stay as written. Each release is one row, with a column per number: the number, **N/A** if it can't exist, or empty if it hasn't been recorded or isn't due yet. A colleague's own field has their name in brackets. The Excel file also has sheets with the units and fields and a **Read me** sheet explaining all this.

The file contains personal data, such as researchers' names. Keep it within the office, and delete copies you no longer need.

## My fields

Numbers you track for yourself, such as clicks on your own links, go here. Open the menu with your name and choose **My fields**, then add a field. Set **Due at** to get a reminder at that checkpoint. Colleagues can see your fields next to your name, and only you can change them.

## Researchers

Editors find **Researchers** in the top navigation, and admins find it under **Settings**. Search by name or identifier. Changes save as soon as you leave a field.

Two different people can share a name, so a name alone never links a release to a record. A record with a namesake shows a small label, **Others with this name**, which finds them when clicked. Tick **Same name only** to see them all. The unit, identifiers and **Notes** tell them apart, so write something in **Notes** when nothing else does, such as a lab or a topic.

To combine two records of the same person, choose **Merge** on the record you want to retire, search for the one to keep and choose **Keep this one**. Its releases move across, and any gaps on the record you keep are filled in.

If that was a mistake, choose **Undo** straight away. Later on, choose **Split** on the record you kept, and then **Undo merge**: the merged record comes back with its releases.

If one record covers two people, choose **Split**, tick the releases of the other person and choose where they go: a new record, which starts with the same name, or one that already exists.

## Settings for admins

**Settings** is only visible to admins, and every section works without changing anything. Changes save themselves when you leave a field. If a colleague changed the same field a moment earlier, you see what they entered and choose which to keep.

- **Institution:** names, time zone, the month the academic year starts, your news website, and where people land after signing in.
- **Users:** invite people and set their role. To remove someone, switch off **Active**: their name stays in the history. If they tracked personal fields, pass those on or make them institution fields here.
- **Lists:** units, fields, writers and vocabularies. To retire an entry, switch off **Active**. Each list can be exported to CSV, edited in a spreadsheet and imported again. An import shows what it would do before anything changes. A column you leave out of the file stays as it is. If a cell can't be used, the import names its row and column and skips only that cell.
- **Form:** rename, hide, require or reorder the fields on a release, and add your own.
- **Checkpoints & reminders:** when numbers are collected and which numbers those are. A checkpoint can fall before the release date: use a negative number, so −3 is three days before. Choose whether its reminder comes at the start of that day or the day before. The reminder emails themselves arrive in a later phase.
- **Data:** backups, a full copy of your data, and what the automatic jobs have been doing.

Release codes are assigned by Release Radar and can't be edited. A release gets its code when its release date is first entered, and keeps it even if the date later moves to another academic year.
