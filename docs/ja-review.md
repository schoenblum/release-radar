# Japanese strings awaiting review

Claude Code drafted the Japanese strings below. A native speaker should review them
(R5.4.7). When a string has been reviewed, change its status to `reviewed`. A corrected
string is edited in its catalogue and here.

`python3 scripts/check_i18n.py --update-ja-review` adds new strings. CI fails if a
Japanese string is not listed.

The whole of `frontend/src/manual/ja.md` is also a draft awaiting review.

| String | English | Japanese | Status |
|---|---|---|---|
| `frontend:app.loading` | Loading… | 読み込み中… | pending |
| `frontend:app.name` | Release Radar | Release Radar | pending |
| `frontend:app.skip_to_content` | Skip to main content | 本文へ移動 | pending |
| `frontend:app.version` | Version {{version}} | バージョン {{version}} | pending |
| `frontend:change_password.back` | Back | 戻る | pending |
| `frontend:change_password.confirm_password` | Repeat the new password | 新しいパスワード（確認） | pending |
| `frontend:change_password.current_password` | Current password | 現在のパスワード | pending |
| `frontend:change_password.forced_notice` | Welcome! Please choose your own password to continue. | ようこそ。続けるには、ご自身のパスワードを設定してください。 | pending |
| `frontend:change_password.hint` | At least 10 characters. | 10 文字以上で入力してください。 | pending |
| `frontend:change_password.new_password` | New password | 新しいパスワード | pending |
| `frontend:change_password.submit` | Save the new password | 新しいパスワードを保存 | pending |
| `frontend:change_password.title` | Change password | パスワードの変更 | pending |
| `frontend:errors.current_password_incorrect` | Your current password isn't right. Please try again. | 現在のパスワードが正しくありません。もう一度お試しください。 | pending |
| `frontend:errors.generic` | Something went wrong. Please try again. | 問題が発生しました。もう一度お試しください。 | pending |
| `frontend:errors.invalid_credentials` | That email and password don't match. Please try again. | メールアドレスとパスワードが一致しません。もう一度お試しください。 | pending |
| `frontend:errors.network` | We can't reach the server. Please check your connection and try again. | サーバーに接続できません。接続を確認して、もう一度お試しください。 | pending |
| `frontend:errors.password_mismatch` | The two new passwords don't match. | 新しいパスワードが一致しません。 | pending |
| `frontend:errors.password_too_long` | That password is too long. Please use a shorter one. | パスワードが長すぎます。短いものをご利用ください。 | pending |
| `frontend:errors.password_too_short` | Please use at least 10 characters. | 10 文字以上で入力してください。 | pending |
| `frontend:errors.password_unchanged` | Please choose a password different from your current one. | 現在のパスワードとは異なるものを設定してください。 | pending |
| `frontend:errors.rate_limited` | Too many attempts. Please wait a few minutes and try again. | 試行回数が多すぎます。数分待ってから、もう一度お試しください。 | pending |
| `frontend:errors.reset_token_invalid` | This link has expired or was already used. Please ask for a new one. | このリンクは有効期限が切れているか、すでに使用されています。新しいリンクを申請してください。 | pending |
| `frontend:errors.session_expired` | Please sign in again. | もう一度サインインしてください。 | pending |
| `frontend:errors.validation_error` | Please check what you entered and try again. | 入力内容を確認して、もう一度お試しください。 | pending |
| `frontend:forgot.back` | Back to sign-in | サインインに戻る | pending |
| `frontend:forgot.email` | Email | メールアドレス | pending |
| `frontend:forgot.email_disabled` | This installation can't send email yet. Please ask an administrator to reset your password. | このシステムはまだメールを送信できません。管理者にパスワードの再設定を依頼してください。 | pending |
| `frontend:forgot.intro` | Enter your email address and we'll send you a link to choose a new password. | メールアドレスを入力してください。新しいパスワードを設定するためのリンクをお送りします。 | pending |
| `frontend:forgot.sent` | If that address has an account, a link is on its way. It works for one hour. | このアドレスのアカウントがあれば、リンクをお送りしました。リンクの有効期間は 1 時間です。 | pending |
| `frontend:forgot.submit` | Send link | リンクを送信 | pending |
| `frontend:forgot.title` | Reset your password | パスワードの再設定 | pending |
| `frontend:language.switch_label` | Switch the language to Japanese | 表示言語を英語に切り替える | pending |
| `frontend:language.switch_to` | 日本語 | English | pending |
| `frontend:login.email` | Email | メールアドレス | pending |
| `frontend:login.forgot` | Forgot your password? | パスワードをお忘れですか？ | pending |
| `frontend:login.password` | Password | パスワード | pending |
| `frontend:login.submit` | Sign in | サインイン | pending |
| `frontend:login.title` | Sign in | サインイン | pending |
| `frontend:nav.all_releases` | All releases | 全リリース | pending |
| `frontend:nav.main` | Main | メイン | pending |
| `frontend:nav.manual` | Manual | マニュアル | pending |
| `frontend:nav.my_releases` | My releases | 担当リリース | pending |
| `frontend:nav.settings` | Settings | 設定 | pending |
| `frontend:nav.writers` | Writers | ライター | pending |
| `frontend:placeholder.all_releases` | All releases, with search, filters and export, will appear here. | 全リリースの検索、絞り込み、エクスポートがここでできるようになります。 | pending |
| `frontend:placeholder.my_releases` | Your releases and the numbers due will appear here. | 担当リリースと入力予定の数値がここに表示されます。 | pending |
| `frontend:placeholder.settings` | Institution details, users, lists and other settings will appear here. | 機関情報、ユーザー、リストなどの設定がここでできるようになります。 | pending |
| `frontend:placeholder.title` | This page is on its way | このページは準備中です | pending |
| `frontend:placeholder.writers` | Monthly release counts per writer will appear here. | ライターごとの月別リリース数がここに表示されます。 | pending |
| `frontend:reset.confirm_password` | Repeat the new password | 新しいパスワード（確認） | pending |
| `frontend:reset.done` | Your password has been changed. You can sign in with it now. | パスワードを変更しました。新しいパスワードでサインインできます。 | pending |
| `frontend:reset.missing_token` | This link is incomplete. Please use the full link from the email, or ask for a new one. | このリンクは不完全です。メールに記載されたリンクをすべてご利用いただくか、新しいリンクを申請してください。 | pending |
| `frontend:reset.new_password` | New password | 新しいパスワード | pending |
| `frontend:reset.request_new` | Ask for a new link | 新しいリンクを申請 | pending |
| `frontend:reset.submit` | Save the new password | 新しいパスワードを保存 | pending |
| `frontend:reset.title` | Choose a new password | 新しいパスワードの設定 | pending |
| `frontend:reset.to_login` | Go to sign-in | サインインへ | pending |
| `frontend:user_menu.change_password` | Change password | パスワードを変更 | pending |
| `frontend:user_menu.open` | Account menu | アカウントメニュー | pending |
| `frontend:user_menu.roles.admin` | Admin | 管理者 | pending |
| `frontend:user_menu.roles.editor` | Editor | 編集者 | pending |
| `frontend:user_menu.roles.viewer` | Viewer | 閲覧者 | pending |
| `frontend:user_menu.sign_out` | Sign out | サインアウト | pending |
| `backend:email.footer` | This message was sent automatically by Release Radar. | このメッセージは Release Radar から自動送信されています。 | pending |
| `backend:email.product` | Release Radar | Release Radar | pending |
| `backend:email.reset.button` | Choose a new password | 新しいパスワードを設定する | pending |
| `backend:email.reset.expiry` | The link works once and stays valid for {minutes} minutes. | このリンクは 1 回のみ、{minutes} 分間有効です。 | pending |
| `backend:email.reset.ignore` | If this wasn't you, you can ignore this message. Your password stays as it is. | 心当たりがない場合は、このメールを無視してください。パスワードは変更されません。 | pending |
| `backend:email.reset.intro` | Someone asked to reset the password for this Release Radar account. Use the button below to choose a new one. | この Release Radar アカウントのパスワード再設定が申請されました。下のボタンから新しいパスワードを設定してください。 | pending |
| `backend:email.reset.subject` | Reset your Release Radar password | Release Radar のパスワード再設定 | pending |
| `backend:email.welcome.button` | Sign in | サインイン | pending |
| `backend:email.welcome.change_notice` | You'll be asked to choose your own password when you first sign in. | 初回サインイン時に、ご自身のパスワードを設定していただきます。 | pending |
| `backend:email.welcome.email_label` | Email | メールアドレス | pending |
| `backend:email.welcome.intro` | An account has been created for you on Release Radar. Sign in with the details below. | Release Radar のアカウントを作成しました。以下の情報でサインインしてください。 | pending |
| `backend:email.welcome.password_label` | Temporary password | 仮パスワード | pending |
| `backend:email.welcome.subject` | Your Release Radar account is ready | Release Radar のアカウントを作成しました | pending |
| `backend:seed.checkpoint.d0` | Release day | リリース当日 | pending |
| `backend:seed.checkpoint.d28` | Day 28 | 28 日目 | pending |
| `backend:seed.measure.altmetric_d0` | Altmetric score, day 0 | Altmetric スコア（0 日目） | pending |
| `backend:seed.measure.altmetric_d28` | Altmetric score, day 28 | Altmetric スコア（28 日目） | pending |
| `backend:seed.measure.ea_views_d0` | EurekAlert embargoed views | EurekAlert エンバーゴ中の閲覧数 | pending |
| `backend:seed.measure.ea_views_d28` | EurekAlert views, day 28 | EurekAlert 閲覧数（28 日目） | pending |
| `backend:seed.measure.hp_views_d28` | Website views, 28 days | ウェブサイト閲覧数（28 日間） | pending |
| `backend:seed.measure.pickups_all` | Pickups, all | ピックアップ数（全体） | pending |
| `backend:seed.measure.pickups_major` | Pickups, major outlets | ピックアップ数（主要メディア） | pending |
| `frontend:common.actions` | Actions | 操作 | pending |
| `frontend:common.active` | Active | 有効 | pending |
| `frontend:common.add` | Add | 追加 | pending |
| `frontend:common.apply` | Apply | 適用 | pending |
| `frontend:common.cancel` | Cancel | キャンセル | pending |
| `frontend:common.coming_later` | Coming in a later phase | 今後のフェーズで追加予定 | pending |
| `frontend:common.export_csv` | Export CSV | CSV をエクスポート | pending |
| `frontend:common.import_csv` | Import CSV | CSV をインポート | pending |
| `frontend:common.move_down` | Move down | 下へ移動 | pending |
| `frontend:common.move_up` | Move up | 上へ移動 | pending |
| `frontend:common.no` | No | いいえ | pending |
| `frontend:common.none` | None | なし | pending |
| `frontend:common.order` | Order | 順序 | pending |
| `frontend:common.personal_data` | This file contains personal data. | このファイルには個人情報が含まれます。 | pending |
| `frontend:common.saved` | Saved | 保存しました | pending |
| `frontend:common.saving` | Saving… | 保存中… | pending |
| `frontend:common.show_more` | Show more | さらに表示 | pending |
| `frontend:common.undo` | Undo | 元に戻す | pending |
| `frontend:common.yes` | Yes | はい | pending |
| `frontend:conflict.empty` | (empty) | （空欄） | pending |
| `frontend:conflict.keep_mine` | Keep mine | 自分の内容を残す | pending |
| `frontend:conflict.message` | Someone else just changed this to “{{value}}”. | 他の方がこの項目を「{{value}}」に変更しました。 | pending |
| `frontend:conflict.use_theirs` | Use theirs | 相手の内容を使う | pending |
| `frontend:csv.did` | Added {{created}}, updated {{updated}}, left {{unchanged}} as they were. | {{created}} 件を追加、{{updated}} 件を更新しました。{{unchanged}} 件は変更していません。 | pending |
| `frontend:csv.problem` | Row {{row}} ({{key}}): {{message}} | {{row}} 行目（{{key}}）：{{message}} | pending |
| `frontend:csv.would` | This would add {{created}}, update {{updated}} and leave {{unchanged}} as they are. | {{created}} 件を追加、{{updated}} 件を更新し、{{unchanged}} 件は変更しません。 | pending |
| `frontend:custom_field.add` | Add field | 項目を追加 | pending |
| `frontend:custom_field.due` | Due at | 入力時点 | pending |
| `frontend:custom_field.due_hint` | Shows up as a reminder at this checkpoint. | このチェックポイントでリマインダーとして表示されます。 | pending |
| `frontend:custom_field.label_en` | Name (EN) | 名称（英語） | pending |
| `frontend:custom_field.label_ja` | Name (JA) | 名称（日本語） | pending |
| `frontend:custom_field.none_yet` | None yet. | まだありません。 | pending |
| `frontend:custom_field.options` | Choices | 選択肢 | pending |
| `frontend:custom_field.options_hint` | One per line, with the Japanese after a bar: Newspaper \| 新聞 | 1 行に 1 つ、英語の後に縦棒で日本語を続けてください：Newspaper \| 新聞 | pending |
| `frontend:custom_field.options_on_field` | Written on this field | この項目で定義 | pending |
| `frontend:custom_field.required` | Required | 必須 | pending |
| `frontend:custom_field.score_eligible` | Can count in scores | スコアに使用可 | pending |
| `frontend:custom_field.type` | Type | 種類 | pending |
| `frontend:custom_field.type_hint` | This can't be changed later. | 後から変更することはできません。 | pending |
| `frontend:custom_field.types.boolean` | Yes or no | はい／いいえ | pending |
| `frontend:custom_field.types.date` | Date | 日付 | pending |
| `frontend:custom_field.types.integer` | Whole number | 整数 | pending |
| `frontend:custom_field.types.long_text` | Long text | 長いテキスト | pending |
| `frontend:custom_field.types.multi_select` | Several choices | 複数選択 | pending |
| `frontend:custom_field.types.number` | Number | 数値 | pending |
| `frontend:custom_field.types.single_select` | One choice | 単一選択 | pending |
| `frontend:custom_field.types.text` | Short text | 短いテキスト | pending |
| `frontend:custom_field.types.url` | Web address | ウェブアドレス | pending |
| `frontend:custom_field.vocabulary` | Vocabulary | 語彙リスト | pending |
| `frontend:errors.admin_required` | Only admins can do this. | 管理者のみ操作できます。 | pending |
| `frontend:errors.backup_not_configured` | Backups aren't set up on this server. | このサーバーではバックアップが設定されていません。 | pending |
| `frontend:errors.cannot_deactivate_self` | You can't switch off your own account. | ご自身のアカウントは無効にできません。 | pending |
| `frontend:errors.cannot_demote_self` | You can't change your own role. | ご自身の権限は変更できません。 | pending |
| `frontend:errors.conflict` | Someone else changed this at the same moment. Please look again and try once more. | 他の方が同時に変更しました。内容を確認して、もう一度お試しください。 | pending |
| `frontend:errors.core_field_locked` | Release Radar relies on this, so it can't be changed. | Release Radar の動作に必要なため、変更できません。 | pending |
| `frontend:errors.csv_missing_column` | This file is missing the column that identifies each row. | このファイルには、各行を識別する列がありません。 | pending |
| `frontend:errors.editor_required` | Only editors and admins can do this. | 編集者と管理者のみ操作できます。 | pending |
| `frontend:errors.email_in_use` | Someone already uses that email address. | このメールアドレスはすでに使用されています。 | pending |
| `frontend:errors.field_invalid` | That value isn't valid here. | この値は使用できません。 | pending |
| `frontend:errors.field_not_editable` | This can't be changed. | この項目は変更できません。 | pending |
| `frontend:errors.field_out_of_range` | That number is outside the allowed range. | 数値が許容範囲を超えています。 | pending |
| `frontend:errors.field_required` | This can't be empty. | 入力してください。 | pending |
| `frontend:errors.field_too_long` | That's too long. Please shorten it. | 長すぎます。短くしてください。 | pending |
| `frontend:errors.invalid_code_pattern` | The pattern needs both {yyyy} and {nn}, and nothing else in braces. | 形式には {yyyy} と {nn} の両方が必要で、波括弧はこの 2 つにのみ使えます。 | pending |
| `frontend:errors.invalid_domain` | Please enter an address like news.example.org. | news.example.org のようなアドレスを入力してください。 | pending |
| `frontend:errors.invalid_email` | Please enter a valid email address. | 正しいメールアドレスを入力してください。 | pending |
| `frontend:errors.invalid_timezone` | Please choose a time zone from the list. | リストからタイムゾーンを選択してください。 | pending |
| `frontend:errors.measure_locked` | This goes live with its phase, later on. | 今後のフェーズで有効になります。 | pending |
| `frontend:errors.merge_into_self` | A record can't be merged into itself. | 同じレコードには統合できません。 | pending |
| `frontend:errors.not_found` | That no longer exists. It may have been changed by someone else. | 見つかりません。他の方によって変更された可能性があります。 | pending |
| `frontend:errors.owner_must_edit` | A field can only pass to an active editor or admin. | 引き継ぎ先は、有効な編集者または管理者のみです。 | pending |
| `frontend:errors.personal_field_read_only` | Only its owner can change a personal field. | 個人用の項目は所有者のみ変更できます。 | pending |
| `frontend:errors.researcher_merged` | This record was merged into another one. | このレコードは別のレコードに統合されています。 | pending |
| `frontend:errors.score_eligible_numeric_only` | Only number fields can count in scores. | スコアに使えるのは数値の項目のみです。 | pending |
| `frontend:errors.unknown_reference` | That entry doesn't exist. | その項目は存在しません。 | pending |
| `frontend:errors.use_change_password` | Please use Change password for your own account. | ご自身のアカウントは「パスワードを変更」から変更してください。 | pending |
| `frontend:errors.value_in_use` | That's already in use. Please choose another. | すでに使用されています。別の値にしてください。 | pending |
| `frontend:my_fields.help` | Numbers you track for yourself. Colleagues can see them next to your name, and only you can change them. | ご自身で記録する項目です。同僚にはお名前とともに表示されますが、変更できるのはご本人だけです。 | pending |
| `frontend:my_fields.title` | My fields | マイフィールド | pending |
| `frontend:nav.researchers` | Researchers | 研究者 | pending |
| `frontend:release_fields.also_featured` | Also featured | その他の掲載者 | pending |
| `frontend:release_fields.authors` | Authors | 著者 | pending |
| `frontend:release_fields.code` | Code | コード | pending |
| `frontend:release_fields.doi` | DOI | DOI | pending |
| `frontend:release_fields.ea_top_page` | EurekAlert top page | EurekAlert トップページ掲載 | pending |
| `frontend:release_fields.ea_top_position` | Top page position | トップページの掲載順 | pending |
| `frontend:release_fields.ea_url` | EurekAlert link | EurekAlert のリンク | pending |
| `frontend:release_fields.embargoed` | Embargoed | エンバーゴあり | pending |
| `frontend:release_fields.field` | Field | 分野 | pending |
| `frontend:release_fields.journal` | Journal | 掲載誌 | pending |
| `frontend:release_fields.notes` | Notes | メモ | pending |
| `frontend:release_fields.paper_title` | Paper title | 論文タイトル | pending |
| `frontend:release_fields.publication_date` | Publication date | 論文の発表日 | pending |
| `frontend:release_fields.release_date` | Release date | リリース日 | pending |
| `frontend:release_fields.release_time_et` | Release time (ET) | リリース時刻（米国東部時間） | pending |
| `frontend:release_fields.researcher` | Researcher | 研究者 | pending |
| `frontend:release_fields.title` | Title | タイトル | pending |
| `frontend:release_fields.title_ja` | Title (Japanese) | タイトル（日本語） | pending |
| `frontend:release_fields.unit` | Unit | 部局 | pending |
| `frontend:release_fields.website_url` | Website link | ウェブサイトのリンク | pending |
| `frontend:release_fields.writer` | Writer | ライター | pending |
| `frontend:researchers.add` | Add a researcher | 研究者を追加 | pending |
| `frontend:researchers.all_statuses` | All statuses | すべての状態 | pending |
| `frontend:researchers.family_name` | Family name | 姓 | pending |
| `frontend:researchers.found` | Researchers found: {{count}} | 該当する研究者：{{count}} 名 | pending |
| `frontend:researchers.gender` | Gender | 性別 | pending |
| `frontend:researchers.genders.F` | Female | 女性 | pending |
| `frontend:researchers.genders.M` | Male | 男性 | pending |
| `frontend:researchers.genders.not_recorded` | Not recorded | 未記録 | pending |
| `frontend:researchers.genders.other` | Other | その他 | pending |
| `frontend:researchers.given_name` | Given name | 名 | pending |
| `frontend:researchers.merge` | Merge | 統合 | pending |
| `frontend:researchers.merge_choose` | Keep this one | こちらを残す | pending |
| `frontend:researchers.merge_hint` | Search for the record to keep. Its details stay, and gaps are filled from this one. | 残すレコードを検索してください。そのレコードの内容は保持され、空欄のみこのレコードの内容で補います。 | pending |
| `frontend:researchers.merge_into` | Merge {{name}} into: | {{name}} の統合先： | pending |
| `frontend:researchers.merge_question` | Move {{count}} release(s) to {{name}} and retire this record? | {{count}} 件のリリースを {{name}} に移し、このレコードを統合しますか？ | pending |
| `frontend:researchers.merged` | {{from}} was merged into {{to}}. | {{from}} を {{to}} に統合しました。 | pending |
| `frontend:researchers.name` | Name as entered | 入力された氏名 | pending |
| `frontend:researchers.name_ja` | Name (JA) | 氏名（日本語） | pending |
| `frontend:researchers.orcid` | ORCID | ORCID | pending |
| `frontend:researchers.release_total` | Releases: {{count}} | リリース数：{{count}} | pending |
| `frontend:researchers.releases` | Releases | リリース数 | pending |
| `frontend:researchers.researchmap` | researchmap | researchmap | pending |
| `frontend:researchers.search` | Search by name or identifier | 氏名または識別子で検索 | pending |
| `frontend:researchers.status` | Status | 状態 | pending |
| `frontend:researchers.statuses.incomplete` | Incomplete | 未完了 | pending |
| `frontend:researchers.statuses.unverified` | Unverified | 未確認 | pending |
| `frontend:researchers.statuses.verified` | Verified | 確認済み | pending |
| `frontend:researchers.unit` | Current unit | 現在の所属 | pending |
| `frontend:settings.checkpoints.add` | Add checkpoint | チェックポイントを追加 | pending |
| `frontend:settings.checkpoints.add_measure` | Add measure | 測定項目を追加 | pending |
| `frontend:settings.checkpoints.applies` | Applies to | 対象 | pending |
| `frontend:settings.checkpoints.at_checkpoint` | At checkpoint | チェックポイント | pending |
| `frontend:settings.checkpoints.checkpoints_title` | Checkpoints | チェックポイント | pending |
| `frontend:settings.checkpoints.collected_from` | Collected from | 収集開始日 | pending |
| `frontend:settings.checkpoints.label_en` | Name (EN) | 名称（英語） | pending |
| `frontend:settings.checkpoints.label_ja` | Name (JA) | 名称（日本語） | pending |
| `frontend:settings.checkpoints.locked` | Goes live with pickups, in a later phase. | 今後のフェーズでピックアップ機能とともに有効になります。 | pending |
| `frontend:settings.checkpoints.measures_help` | The numbers collected at each checkpoint. Switching one off keeps what was recorded. | 各チェックポイントで収集する数値です。無効にしても、記録済みの値は保持されます。 | pending |
| `frontend:settings.checkpoints.measures_title` | Measures | 測定項目 | pending |
| `frontend:settings.checkpoints.metric` | Number | 数値 | pending |
| `frontend:settings.checkpoints.metrics.altmetric` | Altmetric score | Altmetric スコア | pending |
| `frontend:settings.checkpoints.metrics.ea_views` | EurekAlert views | EurekAlert 閲覧数 | pending |
| `frontend:settings.checkpoints.metrics.hp_views` | Website views | ウェブサイト閲覧数 | pending |
| `frontend:settings.checkpoints.offset` | Days after release | リリース後の日数 | pending |
| `frontend:settings.checkpoints.reminders_later` | Reminder settings arrive with the reminders themselves, in a later phase. | リマインダーの設定は、今後のフェーズで機能とともに追加されます。 | pending |
| `frontend:settings.checkpoints.reminders_title` | Reminders | リマインダー | pending |
| `frontend:settings.checkpoints.rules.always` | All releases | 全リリース | pending |
| `frontend:settings.checkpoints.rules.embargoed` | Embargoed releases | エンバーゴ付きのリリース | pending |
| `frontend:settings.checkpoints.rules.has_doi` | Releases with a DOI | DOI のあるリリース | pending |
| `frontend:settings.checkpoints.rules.has_ea_url` | Releases with a EurekAlert link | EurekAlert のリンクがあるリリース | pending |
| `frontend:settings.checkpoints.rules.website_on_domain` | Releases on your website | 自機関サイト上のリリース | pending |
| `frontend:settings.checkpoints.source` | Comes from | 取得元 | pending |
| `frontend:settings.checkpoints.sources.derived` | Calculated | 自動集計 | pending |
| `frontend:settings.checkpoints.sources.ga4` | Google Analytics | Google Analytics | pending |
| `frontend:settings.checkpoints.sources.manual` | Entered by hand | 手入力 | pending |
| `frontend:settings.data.backup_keeps` | Kept for | 保存期間 | pending |
| `frontend:settings.data.backup_last_run` | Last run | 前回の実行 | pending |
| `frontend:settings.data.backup_latest` | Latest backup | 最新のバックアップ | pending |
| `frontend:settings.data.backup_none` | None yet | まだありません | pending |
| `frontend:settings.data.backup_not_configured` | Backups are off, because no passphrase is set on the server. Please ask whoever runs the server. | サーバーにパスフレーズが設定されていないため、バックアップは無効です。サーバーの管理者にご相談ください。 | pending |
| `frontend:settings.data.backup_now` | Back up now | 今すぐバックアップ | pending |
| `frontend:settings.data.backup_retention` | {{days}} days | {{days}} 日間 | pending |
| `frontend:settings.data.backup_started` | Backup started. | バックアップを開始しました。 | pending |
| `frontend:settings.data.backup_title` | Backups | バックアップ | pending |
| `frontend:settings.data.export_help` | A complete copy of your data for safekeeping. Passwords and sessions are left out. | 保管用の全データのコピーです。パスワードとセッション情報は含まれません。 | pending |
| `frontend:settings.data.export_json` | Download JSON | JSON をダウンロード | pending |
| `frontend:settings.data.export_title` | Full export | 全データのエクスポート | pending |
| `frontend:settings.data.export_xlsx` | Download Excel | Excel をダウンロード | pending |
| `frontend:settings.data.import_later` | Importing the existing workbook arrives in a later step. | 既存のワークブックのインポートは、今後のステップで追加されます。 | pending |
| `frontend:settings.data.import_title` | Import | インポート | pending |
| `frontend:settings.data.job` | Job | 処理 | pending |
| `frontend:settings.data.job_detail` | Details | 詳細 | pending |
| `frontend:settings.data.job_result` | Result | 結果 | pending |
| `frontend:settings.data.job_when` | When | 日時 | pending |
| `frontend:settings.data.jobs.backup-nightly` | Nightly backup | 夜間バックアップ | pending |
| `frontend:settings.data.jobs.backup-manual` | Backup on request | 手動バックアップ | pending |
| `frontend:settings.data.jobs.housekeeping` | Housekeeping | 定期メンテナンス | pending |
| `frontend:settings.data.jobs.scheduler-test` | Scheduler test | スケジューラーのテスト | pending |
| `frontend:settings.data.jobs_none` | Nothing has run yet. | まだ実行されていません。 | pending |
| `frontend:settings.data.jobs_title` | Automatic jobs | 自動処理 | pending |
| `frontend:settings.data.status.failed` | Failed | 失敗 | pending |
| `frontend:settings.data.status.running` | Running | 実行中 | pending |
| `frontend:settings.data.status.skipped` | Skipped | スキップ | pending |
| `frontend:settings.data.status.succeeded` | Done | 完了 | pending |
| `frontend:settings.form.cannot_hide` | Release Radar relies on this field, so it stays visible. | Release Radar の動作に必要なため、非表示にできません。 | pending |
| `frontend:settings.form.cannot_require` | Release Radar assigns this itself. | Release Radar が自動で付与する項目です。 | pending |
| `frontend:settings.form.core_help` | Leave a label empty to keep the standard one. Hidden fields keep their data. | 名称を空欄にすると標準の名称を使います。非表示にした項目のデータは保持されます。 | pending |
| `frontend:settings.form.core_title` | Built-in fields | 標準項目 | pending |
| `frontend:settings.form.custom_help` | Extra fields for everyone in your institution. Personal ones are under My fields in the account menu. | 機関の全員が使う追加項目です。個人用の項目はアカウントメニューの「マイフィールド」で管理します。 | pending |
| `frontend:settings.form.custom_title` | Your own fields | 独自項目 | pending |
| `frontend:settings.form.field` | Field | 項目 | pending |
| `frontend:settings.form.hidden` | Hidden | 非表示 | pending |
| `frontend:settings.form.label_en` | Label (EN) | 名称（英語） | pending |
| `frontend:settings.form.label_ja` | Label (JA) | 名称（日本語） | pending |
| `frontend:settings.form.required` | Required | 必須 | pending |
| `frontend:settings.help.checkpoints` | The moments after a release when numbers are collected, and which numbers those are. | リリース後に数値を収集する時点と、収集する数値を設定します。 | pending |
| `frontend:settings.help.data` | Your backups, a full copy of your data, and what the automatic jobs have been doing. | バックアップ、全データのエクスポート、自動処理の実行状況を確認できます。 | pending |
| `frontend:settings.help.form` | Adapt the fields on a release: rename, hide, require or reorder them, or add your own. | リリースの項目を調整します。名称変更、非表示、必須、並べ替え、独自項目の追加ができます。 | pending |
| `frontend:settings.help.institution` | Who you are and how the tool counts years. The defaults work, so change only what differs. | 機関の情報と年度の数え方を設定します。初期設定のままでも使えるので、異なる点だけ変更してください。 | pending |
| `frontend:settings.help.lists` | The values people choose from. To retire an entry, switch off Active: releases that use it keep it. | 選択肢となる値です。使わなくなった項目は「有効」をオフにしてください。その項目を使っているリリースはそのまま残ります。 | pending |
| `frontend:settings.help.researchers` | Everyone named on a release. Tidy up names, add identifiers and merge duplicates. Nothing here changes any statistics, because releases refer to the record and not the name. | リリースに登場する研究者です。氏名の整理、識別子の追加、重複の統合ができます。リリースは氏名ではなくレコードを参照するため、統計には影響しません。 | pending |
| `frontend:settings.help.users` | Invite people and choose what they can do. People are switched off rather than deleted, so their name stays in the history. | ユーザーを招待し、権限を設定します。ユーザーは削除せず無効にするため、履歴に名前が残ります。 | pending |
| `frontend:settings.institution.ay_start` | Academic year starts in | 年度の開始月 | pending |
| `frontend:settings.institution.code_pattern` | Release code pattern | リリースコードの形式 | pending |
| `frontend:settings.institution.code_pattern_hint` | Release Radar assigns the codes itself. {yyyy} is the academic year and {nn} the number. A change affects new codes only: existing codes never change. | コードは Release Radar が自動で付与します。{yyyy} は年度、{nn} は番号です。変更は新しいコードにのみ適用され、既存のコードは変わりません。 | pending |
| `frontend:settings.institution.contact_email` | Office contact address | 事務局の連絡先アドレス | pending |
| `frontend:settings.institution.contact_email_hint` | Sent to Crossref when looking up papers. Use a shared office address, not a person's. | 論文情報の検索時に Crossref へ送信されます。個人ではなく、部署の共有アドレスを指定してください。 | pending |
| `frontend:settings.institution.landing` | Where people land | サインイン後の表示ページ | pending |
| `frontend:settings.institution.landing_all` | All releases | 全リリース | pending |
| `frontend:settings.institution.landing_hint` | The first page after signing in. Someone with no writer entry always lands on all releases. | サインイン後に最初に表示するページです。ライターとして登録されていない方には、常に全リリースを表示します。 | pending |
| `frontend:settings.institution.landing_mine` | Their own releases | 担当リリース | pending |
| `frontend:settings.institution.name_en` | Name (English) | 機関名（英語） | pending |
| `frontend:settings.institution.name_ja` | Name (Japanese) | 機関名（日本語） | pending |
| `frontend:settings.institution.timezone` | Time zone | タイムゾーン | pending |
| `frontend:settings.institution.timezone_hint` | Dates show in this time zone. Nightly jobs switch over at the next restart. | 日付はこのタイムゾーンで表示されます。夜間の自動処理には次回の再起動後に反映されます。 | pending |
| `frontend:settings.institution.website_domain` | News website address | ニュースサイトのアドレス | pending |
| `frontend:settings.institution.website_domain_hint` | Website views count only for releases on exactly this address, for example news.example.org. | ウェブサイト閲覧数は、このアドレス上のリリースのみが対象です（例：news.example.org）。 | pending |
| `frontend:settings.lists.add_field` | Add a field | 分野を追加 | pending |
| `frontend:settings.lists.add_item` | Add an item | 項目を追加 | pending |
| `frontend:settings.lists.add_unit` | Add a unit | 部局を追加 | pending |
| `frontend:settings.lists.add_vocabulary` | Add a vocabulary | 語彙リストを追加 | pending |
| `frontend:settings.lists.add_writer` | Add a writer | ライターを追加 | pending |
| `frontend:settings.lists.aliases` | Aliases | 別名 | pending |
| `frontend:settings.lists.default_field` | Default field | 既定の分野 | pending |
| `frontend:settings.lists.display_name_en` | Name shown (EN) | 表示名（英語） | pending |
| `frontend:settings.lists.display_name_ja` | Name shown (JA) | 表示名（日本語） | pending |
| `frontend:settings.lists.full_name` | Full name | 氏名 | pending |
| `frontend:settings.lists.items_of` | Items in {{name}} | 「{{name}}」の項目 | pending |
| `frontend:settings.lists.kinds.fields` | Fields | 分野 | pending |
| `frontend:settings.lists.kinds.units` | Units | 部局 | pending |
| `frontend:settings.lists.kinds.vocabularies` | Vocabularies | 語彙リスト | pending |
| `frontend:settings.lists.kinds.writers` | Writers | ライター | pending |
| `frontend:settings.lists.linked_user` | Account | アカウント | pending |
| `frontend:settings.lists.name_en` | Name (EN) | 名称（英語） | pending |
| `frontend:settings.lists.name_ja` | Name (JA) | 名称（日本語） | pending |
| `frontend:settings.lists.no_account` | No account | アカウントなし | pending |
| `frontend:settings.lists.scope_note` | What belongs here | 対象範囲 | pending |
| `frontend:settings.lists.short_label` | Short label | 略称 | pending |
| `frontend:settings.lists.show_items` | Show items | 項目を表示 | pending |
| `frontend:settings.lists.type` | Type | 種別 | pending |
| `frontend:settings.lists.types.center` | Center | センター | pending |
| `frontend:settings.lists.types.institute` | Institute | 研究所 | pending |
| `frontend:settings.lists.types.other` | Other | その他 | pending |
| `frontend:settings.lists.types.school` | School | 研究科・学部 | pending |
| `frontend:settings.lists.vocabularies_help` | Named lists of choices for custom fields, in both languages. | カスタム項目で使う選択肢のリストです（英語・日本語）。 | pending |
| `frontend:settings.lists.writers_help` | Writers need no account, so former staff can stay on their releases. | ライターにアカウントは不要です。退職された方も、担当リリースに名前を残せます。 | pending |
| `frontend:settings.sections.checkpoints` | Checkpoints & reminders | チェックポイントとリマインダー | pending |
| `frontend:settings.sections.data` | Data | データ | pending |
| `frontend:settings.sections.form` | Form | 入力フォーム | pending |
| `frontend:settings.sections.institution` | Institution | 機関情報 | pending |
| `frontend:settings.sections.integrations` | Integrations | 外部連携 | pending |
| `frontend:settings.sections.lists` | Lists | リスト | pending |
| `frontend:settings.sections.outlets` | Outlets | メディア | pending |
| `frontend:settings.sections.researchers` | Researchers | 研究者 | pending |
| `frontend:settings.sections.score_profiles` | Score profiles | スコアプロファイル | pending |
| `frontend:settings.sections.survey` | Survey | アンケート | pending |
| `frontend:settings.sections.users` | Users | ユーザー | pending |
| `frontend:settings.users.email` | Email | メールアドレス | pending |
| `frontend:settings.users.email_language` | Language of the email | メールの言語 | pending |
| `frontend:settings.users.former_user` | former user | 元ユーザー | pending |
| `frontend:settings.users.invite` | Send invitation | 招待を送信 | pending |
| `frontend:settings.users.invited` | Invitation sent to {{email}}. | {{email}} に招待を送信しました。 | pending |
| `frontend:settings.users.language_english_default` | English | 英語 | pending |
| `frontend:settings.users.language_japanese` | Japanese | 日本語 | pending |
| `frontend:settings.users.last_sign_in` | Last sign-in | 最終サインイン | pending |
| `frontend:settings.users.name` | Name | 氏名 | pending |
| `frontend:settings.users.never` | Never | なし | pending |
| `frontend:settings.users.new_password` | New temporary password | 仮パスワードを再発行 | pending |
| `frontend:settings.users.new_password_question` | Sign them out and send a new one? | サインアウトさせて、新しい仮パスワードを送信しますか？ | pending |
| `frontend:settings.users.no_email` | The email couldn't be sent. Please pass this temporary password on to {{email}} yourself: | メールを送信できませんでした。次の仮パスワードを {{email}} にお伝えください： | pending |
| `frontend:settings.users.people` | People | ユーザー一覧 | pending |
| `frontend:settings.users.personal_convert` | Make institution field | 機関共通の項目にする | pending |
| `frontend:settings.users.personal_convert_question` | Everyone will use this field from now on. Continue? | 今後は全員がこの項目を使うことになります。続けますか？ | pending |
| `frontend:settings.users.personal_field` | Field | 項目 | pending |
| `frontend:settings.users.personal_help` | Fields people track for themselves. When someone leaves, pass theirs on or make them institution fields. The values stay either way. | 各自が記録している項目です。担当者が異動・退職した場合は、他の方に引き継ぐか機関共通の項目に変更してください。どちらの場合も値は保持されます。 | pending |
| `frontend:settings.users.personal_owner` | Owner | 所有者 | pending |
| `frontend:settings.users.personal_title` | Personal fields | 個人用フィールド | pending |
| `frontend:settings.users.personal_transfer` | Pass on to | 引き継ぎ先 | pending |
| `frontend:settings.users.reset_sent` | A new temporary password was emailed to {{email}}. | 新しい仮パスワードを {{email}} に送信しました。 | pending |
| `frontend:settings.users.role` | Role | 権限 | pending |
| `frontend:settings.users.switched_off` | {{email}} was switched off. | {{email}} を無効にしました。 | pending |
| `frontend:user_menu.my_fields` | My fields | マイフィールド | pending |
