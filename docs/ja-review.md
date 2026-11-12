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
| `frontend:nav.main` | Main | メイン | pending |
| `frontend:nav.manual` | Manual | マニュアル | pending |
| `frontend:nav.settings` | Settings | 設定 | pending |
| `frontend:nav.writers` | Writers | ライター | pending |
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
| `frontend:researchers.merge_hint` | Search for the record to keep. Its details stay, and gaps are filled from this one. You can undo this later, under Split. | 残すレコードを検索してください。残すレコードの内容はそのまま保たれ、空欄はこのレコードの内容で補われます。統合は後から「分割」で取り消せます。 | pending |
| `frontend:researchers.merge_into` | Merge {{name}} into: | {{name}} の統合先： | pending |
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
| `frontend:settings.checkpoints.offset` | Days from release | リリース日からの日数 | pending |
| `frontend:settings.checkpoints.reminders_later` | The choice above is saved already. The reminder emails themselves arrive in a later phase. | 上記の選択はすでに保存されています。リマインダーメールの送信は、今後のフェーズで開始します。 | pending |
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
| `frontend:settings.data.import_title` | Import the old workbook | 既存のワークブックをインポート | pending |
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
| `frontend:settings.help.checkpoints` | The moments around a release when numbers are collected, and which numbers those are. | リリースの前後で数値を収集する時点と、収集する数値を設定します。 | pending |
| `frontend:settings.help.data` | Your backups, a full copy of your data, and what the automatic jobs have been doing. | バックアップ、全データのエクスポート、自動処理の実行状況を確認できます。 | pending |
| `frontend:settings.help.form` | Adapt the fields on a release: rename, hide, require or reorder them, or add your own. | リリースの項目を調整します。名称変更、非表示、必須、並べ替え、独自項目の追加ができます。 | pending |
| `frontend:settings.help.institution` | Who you are and how the tool counts years. The defaults work, so change only what differs. | 機関の情報と年度の数え方を設定します。初期設定のままでも使えるので、異なる点だけ変更してください。 | pending |
| `frontend:settings.help.lists` | The values people choose from. To retire an entry, switch off Active: releases that use it keep it. | 選択肢となる値です。使わなくなった項目は「有効」をオフにしてください。その項目を使っているリリースはそのまま残ります。 | pending |
| `frontend:settings.help.researchers` | Everyone named on a release. Tidy up names, add identifiers, merge duplicates and split records that cover two people. Nothing here changes any statistics, because releases refer to the record and not the name. | リリースに記載された研究者の一覧です。氏名の整理、識別子の追加、重複の統合、2 人分をまとめてしまったレコードの分割ができます。リリースは氏名ではなくレコードを参照しているため、統計には影響しません。 | pending |
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
| `frontend:csv.allowed` | Please use one of: {{values}}. | 次のいずれかを使用してください：{{values}} | pending |
| `frontend:csv.problem_cell` | Row {{row}} ({{key}}), column “{{column}}”: {{message}} | {{row}} 行目（{{key}}）、「{{column}}」列：{{message}} | pending |
| `frontend:csv.problem_row` | Row {{row}} ({{key}}): {{message}} | {{row}} 行目（{{key}}）：{{message}} | pending |
| `frontend:csv.problem_value` | “{{value}}” can't be used. {{reason}} | 「{{value}}」は使用できません。{{reason}} | pending |
| `frontend:csv.skipped_did` | These were skipped. The rest of each row was applied: | 以下はスキップしました。各行のその他の内容は適用しました： | pending |
| `frontend:csv.skipped_would` | These would be skipped. The rest of each row still applies: | 以下はスキップされます。各行のその他の内容は適用されます： | pending |
| `frontend:errors.invalid_doi` | Please enter a DOI like 10.1234/example, or a doi.org link. | 10.1234/example の形式の DOI、または doi.org のリンクを入力してください。 | pending |
| `frontend:errors.invalid_time` | Please enter a time like 09:30. | 09:30 の形式で時刻を入力してください。 | pending |
| `frontend:errors.invalid_url` | Please enter a web address starting with https://. | https:// で始まるウェブアドレスを入力してください。 | pending |
| `frontend:errors.release_moved` | One of these releases has already moved. Please look again. | 選択したリリースのいずれかはすでに移動されています。もう一度ご確認ください。 | pending |
| `frontend:errors.researcher_not_merged` | This record isn't merged into another one. | このレコードは他のレコードに統合されていません。 | pending |
| `frontend:errors.split_into_self` | These releases are already on that record. | これらのリリースはすでにそのレコードにあります。 | pending |
| `frontend:errors.title_or_doi_required` | A release needs a title or a DOI. | リリースにはタイトルまたは DOI が必要です。 | pending |
| `frontend:errors.whole_number_required` | Please enter a whole number. | 整数を入力してください。 | pending |
| `frontend:researchers.merge_undone` | The merge was undone. | 統合を取り消しました。 | pending |
| `frontend:researchers.merged_entry` | {{name}}, merged on {{date}} (releases: {{count}}) | {{name}}（{{date}} に統合、リリース {{count}} 件） | pending |
| `frontend:researchers.merged_title` | Merged into this record | このレコードに統合されたレコード | pending |
| `frontend:researchers.no_code` | (no code yet) | （コード未付与） | pending |
| `frontend:researchers.no_title` | (no title yet) | （タイトル未入力） | pending |
| `frontend:researchers.notes` | Notes | メモ | pending |
| `frontend:researchers.notes_hint` | Anything that tells namesakes apart, such as a lab or a topic. | 所属研究室や研究テーマなど、同姓同名の方を区別できる情報。 | pending |
| `frontend:researchers.same_name` | Others with this name: {{count}} | 同じ氏名の他のレコード：{{count}} 件 | pending |
| `frontend:researchers.same_name_only` | Same name only | 同じ氏名のみ | pending |
| `frontend:researchers.split` | Split | 分割 | pending |
| `frontend:researchers.split_done` | Releases moved to {{name}}: {{count}} | {{name}} に移動したリリース：{{count}} 件 | pending |
| `frontend:researchers.split_existing` | An existing record | 既存のレコード | pending |
| `frontend:researchers.split_hint` | For when one record covers two people. Tick the releases that belong to the other person. | 1 つのレコードに 2 人分がまとまっている場合に使います。もう 1 人のリリースにチェックを入れてください。 | pending |
| `frontend:researchers.split_move` | Move selected ({{count}}) | 選択したリリースを移動（{{count}} 件） | pending |
| `frontend:researchers.split_new` | A new record | 新しいレコード | pending |
| `frontend:researchers.split_new_name` | Name of the new record | 新しいレコードの氏名 | pending |
| `frontend:researchers.split_new_notes` | How to tell them apart (optional) | 区別するための情報（任意） | pending |
| `frontend:researchers.split_none` | This record has no releases to move. | このレコードに移動できるリリースはありません。 | pending |
| `frontend:researchers.split_target` | Move them to | 移動先 | pending |
| `frontend:researchers.split_title` | Move releases from {{name}} to another record | {{name}} のリリースを別のレコードに移動 | pending |
| `frontend:researchers.unmerge` | Undo merge | 統合を取り消す | pending |
| `frontend:researchers.unmerged` | {{name}} is a separate record again. | {{name}} は再び別のレコードになりました。 | pending |
| `frontend:settings.checkpoints.offset_help` | A negative number falls before the release date: −3 is three days before. Reminders go out at the start of the day you choose. | 負の数はリリース日より前の日を表します。−3 は 3 日前です。リマインダーは選択した日の朝に送信されます。 | pending |
| `frontend:settings.checkpoints.remind` | Remind | リマインダー | pending |
| `frontend:settings.checkpoints.remind_day_before` | The day before | 前日 | pending |
| `frontend:settings.checkpoints.remind_on_day` | On the day | 当日 | pending |
| `frontend:errors.researcher_in_use` | This record is still in use, so it stays. | このレコードは使用中のため、削除できません。 | pending |
| `frontend:data.authors_hint` | One per line. | 1 行に 1 名ずつ入力してください。 | pending |
| `frontend:data.caught_up` | All caught up. Nothing is due. | すべて入力済みです。現在入力が必要な項目はありません。 | pending |
| `frontend:data.change` | Change | 変更 | pending |
| `frontend:data.clear_na` | Clear N/A | 該当なしを解除 | pending |
| `frontend:data.close` | Close | 閉じる | pending |
| `frontend:data.code_hint` | Assigned when a release date is first entered. | リリース日を初めて入力したときに付与されます。 | pending |
| `frontend:data.column_groups.colleagues` | Colleagues' fields | 同僚の項目 | pending |
| `frontend:data.column_groups.custom` | Your fields and the institution's | 個人用・機関共通の項目 | pending |
| `frontend:data.column_groups.numbers` | Numbers | 数値 | pending |
| `frontend:data.column_groups.paper` | Paper | 論文 | pending |
| `frontend:data.column_groups.release` | Release | リリース | pending |
| `frontend:data.columns` | Columns | 表示項目 | pending |
| `frontend:data.columns_not_saved` | Your column choice couldn't be saved. It applies until you leave this page. | 表示項目の選択を保存できませんでした。このページを離れるまでは適用されます。 | pending |
| `frontend:data.coming_up` | Coming up {{date}} | まもなく {{date}} | pending |
| `frontend:data.count` | Showing {{count}} of {{total}} | {{total}} 件中 {{count}} 件を表示 | pending |
| `frontend:data.crossref_found` | Found the paper: {{title}} | 論文が見つかりました：{{title}} | pending |
| `frontend:data.crossref_not_found` | Crossref doesn't know this DOI. The release is saved, and the paper details can be typed in. | Crossref にこの DOI は登録されていません。リリースは保存されています。論文情報は手入力できます。 | pending |
| `frontend:data.crossref_unavailable` | Crossref can't be reached just now. The release is saved. You can fetch the paper details later from the release. | 現在 Crossref に接続できません。リリースは保存されています。論文情報は後からリリースの詳細で取得できます。 | pending |
| `frontend:data.drawer_custom` | Other fields | その他の項目 | pending |
| `frontend:data.drawer_history` | History | 履歴 | pending |
| `frontend:data.drawer_numbers` | Numbers | 数値 | pending |
| `frontend:data.drawer_paper` | Paper | 論文 | pending |
| `frontend:data.drawer_release` | Release | リリース | pending |
| `frontend:data.due_count` | Due now: {{count}} | 入力時期を迎えた項目：{{count}} 件 | pending |
| `frontend:data.due_on` | Due {{date}} | 入力時期 {{date}} | pending |
| `frontend:data.due_title` | Due now | 入力時期を迎えた項目 | pending |
| `frontend:data.empty` | No releases here yet. Paste a DOI or type a title above. | リリースはまだありません。上の欄に DOI を貼り付けるかタイトルを入力してください。 | pending |
| `frontend:data.empty_no_writer` | Nothing is yours yet, as you have no writer entry. An admin can link one under Settings → Lists → Writers. | ライターとして登録されていないため、担当のリリースはありません。管理者が 設定 → リスト → ライター で紐付けできます。 | pending |
| `frontend:data.empty_read_only` | No releases here yet. | リリースはまだありません。 | pending |
| `frontend:data.failed_hint` | Press Enter or Backspace to correct it, or Esc to go back to what was there. | Enter または Backspace で修正、Esc で元の値に戻せます。 | pending |
| `frontend:data.grid_label` | Releases | リリース | pending |
| `frontend:data.history_created` | Release created | リリースを作成 | pending |
| `frontend:data.history_note` | Note on {{measure}} | {{measure}} のメモ | pending |
| `frontend:data.history_removed` | Removed | 削除 | pending |
| `frontend:data.history_system` | Release Radar | Release Radar | pending |
| `frontend:data.keys_hint` | Type to edit, Enter to save and go down, Esc to go back, double-click or Shift+Enter for the full record, Cmd/Ctrl+Z to undo. | 入力で編集、Enter で保存して下へ、Esc で取り消し、ダブルクリックか Shift+Enter で詳細、Cmd/Ctrl+Z で元に戻します。 | pending |
| `frontend:data.new_release` | ＋ New release: paste a DOI or type a title, then press Enter | ＋ 新しいリリース：DOI を貼り付けるかタイトルを入力して Enter | pending |
| `frontend:data.not_applicable` | N/A | 該当なし | pending |
| `frontend:data.open_to_fill` | Open to fill in | 開いて入力 | pending |
| `frontend:data.owned_by` | {{label}} ({{owner}}) | {{label}}（{{owner}}） | pending |
| `frontend:data.paste_overflow` | {{count}} didn't fit. | {{count}} 件は範囲に収まりませんでした。 | pending |
| `frontend:data.paste_result` | {{saved}} saved, {{invalid}} invalid: see the highlighted cells. | {{saved}} 件を保存、{{invalid}} 件は入力できませんでした。色の付いたセルをご確認ください。 | pending |
| `frontend:data.paste_skipped` | {{count}} can't be changed here. | {{count}} 件はここでは変更できません。 | pending |
| `frontend:data.reading_note` | Note on {{measure}} | {{measure}} のメモ | pending |
| `frontend:data.reading_note_placeholder` | Note (optional) | メモ（任意） | pending |
| `frontend:data.reading_states.missing` | Waiting for a number | 数値の入力待ち | pending |
| `frontend:data.reading_states.not_applicable` | Doesn't apply | 該当なし | pending |
| `frontend:data.reading_states.not_yet_due` | Not yet due | 入力時期前 | pending |
| `frontend:data.reading_states.value` | Recorded | 入力済み | pending |
| `frontend:data.refetch` | Fetch again from Crossref | Crossref から再取得 | pending |
| `frontend:data.refetch_question` | Replace the journal, paper title, date and authors with Crossref's? | 雑誌名、論文タイトル、日付、著者を Crossref の情報に置き換えますか？ | pending |
| `frontend:data.remove` | Remove this release | このリリースを削除 | pending |
| `frontend:data.removed` | {{name}} was removed. | {{name}} を削除しました。 | pending |
| `frontend:data.researcher_authors` | Authors of the paper | 論文の著者 | pending |
| `frontend:data.researcher_clear` | Remove the researcher | 研究者を外す | pending |
| `frontend:data.researcher_create` | Create a new record: {{name}} | 新しいレコードを作成：{{name}} | pending |
| `frontend:data.researcher_directory` | Researchers | 研究者 | pending |
| `frontend:data.researcher_search` | Search or type a name | 氏名を検索または入力 | pending |
| `frontend:data.set_na` | Set N/A | 該当なしにする | pending |
| `frontend:data.still_needed` | Still needed: {{fields}} | 未入力：{{fields}} | pending |
| `frontend:data.undid` | Undone: {{count}} | 元に戻しました：{{count}} 件 | pending |
| `frontend:data.undo_failed` | That couldn't be undone. Someone may have changed it since. | 元に戻せませんでした。他の方が変更した可能性があります。 | pending |
| `frontend:data.view_label` | Which releases to show | 表示するリリース | pending |
| `frontend:data.views.all` | All | すべて | pending |
| `frontend:data.views.mine` | Mine | 自分の担当 | pending |
| `frontend:data.warnings.ea_url_unusual` | This doesn't look like a EurekAlert release link. It's saved anyway. | EurekAlert のリリースのリンクではないようです。このまま保存されています。 | pending |
| `frontend:data.warnings.website_off_domain` | This isn't on your news website, so website views won't apply. It's saved anyway. | ニュースサイト上のページではないため、ウェブサイトの閲覧数は対象外です。このまま保存されています。 | pending |
| `frontend:errors.researcher_needs_choosing` | A name alone can't say which record is meant. Please choose one in the cell. | 氏名だけではレコードを特定できません。セルで選択してください。 | pending |
| `frontend:nav.data` | Data | データ | pending |
| `frontend:data.not_a_number` | Please enter a number, or - if it doesn't apply. | 数値を入力してください。該当しない場合は - を入力してください。 | pending |
| `frontend:data.count_filtered` | {{count}} of {{total}} match | {{total}} 件中 {{count}} 件が該当 | pending |
| `frontend:data.empty_filtered` | No releases match these filters. | 条件に合うリリースはありません。 | pending |
| `frontend:data.export.button` | Export | エクスポート | pending |
| `frontend:data.export.csv` | CSV (UTF-8) | CSV（UTF-8） | pending |
| `frontend:data.export.download` | Download | ダウンロード | pending |
| `frontend:data.export.everything` | Everything | すべてのリリース | pending |
| `frontend:data.export.format` | Format | 形式 | pending |
| `frontend:data.export.language` | Language | 言語 | pending |
| `frontend:data.export.personal_data` | The file contains personal data, such as researchers' names. Keep it within the office and delete copies you no longer need. | ファイルには研究者の氏名などの個人情報が含まれます。オフィス内で扱い、不要になった複製は削除してください。 | pending |
| `frontend:data.export.preparing` | Preparing… | 準備中… | pending |
| `frontend:data.export.rows` | Releases | 対象 | pending |
| `frontend:data.export.this_view` | As shown ({{count}}) | 表示中のリリース（{{count}} 件） | pending |
| `frontend:data.export.title` | Export releases | リリースをエクスポート | pending |
| `frontend:data.export.xlsx` | Excel, with the lists and a Read me sheet | Excel（リストと説明シート付き） | pending |
| `frontend:data.filters.any_field` | Any field | すべての分野 | pending |
| `frontend:data.filters.any_unit` | Any unit | すべての部局 | pending |
| `frontend:data.filters.any_writer` | Any writer | すべてのライター | pending |
| `frontend:data.filters.any_year` | Any year | すべての年度 | pending |
| `frontend:data.filters.clear` | Clear filters | 絞り込みを解除 | pending |
| `frontend:data.filters.clear_one` | Stop filtering by {{name}} | 「{{name}}」での絞り込みをやめる | pending |
| `frontend:data.filters.field` | Field | 分野 | pending |
| `frontend:data.filters.label` | Filters | 絞り込み | pending |
| `frontend:data.filters.researcher` | Researcher | 研究者 | pending |
| `frontend:data.filters.researcher_placeholder` | Any researcher | すべての研究者 | pending |
| `frontend:data.filters.search` | Search releases | リリースを検索 | pending |
| `frontend:data.filters.search_placeholder` | Search titles, names, DOIs, notes | タイトル、氏名、DOI、メモを検索 | pending |
| `frontend:data.filters.unit` | Unit | 部局 | pending |
| `frontend:data.filters.writer` | Writer | ライター | pending |
| `frontend:data.filters.year` | Academic year | 年度 | pending |
| `frontend:data.no_title` | No title yet | タイトル未入力 | pending |
| `frontend:data.paste_saved` | {{count}} saved. | {{count}} 件を保存しました。 | pending |
| `frontend:data.sort_hint` | Sort by {{column}}. Click again to reverse, and a third time for newest first. | {{column}}で並べ替えます。もう一度クリックすると逆順、3 回目で新しい順に戻ります。 | pending |
| `backend:export.fields.academic_year` | Academic year | 年度 | pending |
| `backend:export.fields.also_featured` | Also featured | その他の掲載者 | pending |
| `backend:export.fields.authors` | Authors | 著者 | pending |
| `backend:export.fields.code` | Code | コード | pending |
| `backend:export.fields.doi` | DOI | DOI | pending |
| `backend:export.fields.ea_top_page` | EurekAlert top page | EurekAlert トップページ掲載 | pending |
| `backend:export.fields.ea_top_position` | Top page position | トップページの掲載順 | pending |
| `backend:export.fields.ea_url` | EurekAlert link | EurekAlert のリンク | pending |
| `backend:export.fields.embargoed` | Embargoed | エンバーゴあり | pending |
| `backend:export.fields.field` | Field | 分野 | pending |
| `backend:export.fields.journal` | Journal | 掲載誌 | pending |
| `backend:export.fields.notes` | Notes | メモ | pending |
| `backend:export.fields.paper_title` | Paper title | 論文タイトル | pending |
| `backend:export.fields.publication_date` | Publication date | 論文の発表日 | pending |
| `backend:export.fields.release_date` | Release date | リリース日 | pending |
| `backend:export.fields.release_time_et` | Release time (ET) | リリース時刻（米国東部時間） | pending |
| `backend:export.fields.researcher` | Researcher | 研究者 | pending |
| `backend:export.fields.title` | Title | タイトル | pending |
| `backend:export.fields.title_ja` | Title (Japanese) | タイトル（日本語） | pending |
| `backend:export.fields.unit` | Unit | 部局 | pending |
| `backend:export.fields.website_url` | Website link | ウェブサイトのリンク | pending |
| `backend:export.fields.writer` | Writer | ライター | pending |
| `backend:export.list_columns.active` | Active | 有効 | pending |
| `backend:export.list_columns.default_field` | Default field | 既定の分野 | pending |
| `backend:export.list_columns.key` | Key | キー | pending |
| `backend:export.list_columns.name` | Name | 名称 | pending |
| `backend:export.list_columns.scope_note` | What belongs here | 対象範囲 | pending |
| `backend:export.list_columns.short_label` | Short label | 略称 | pending |
| `backend:export.list_columns.type` | Type | 種別 | pending |
| `backend:export.owned_by` | {label} ({owner}) | {label}（{owner}） | pending |
| `backend:export.readme.colleagues` | A column with a name in brackets is that person's own field. | 括弧内に氏名のある列は、その人の個人項目です。 | pending |
| `backend:export.readme.exported` | Exported on {when} by {who}. | {when} に {who} がエクスポートしました。 | pending |
| `backend:export.readme.filters` | Shown: {filters}. | 表示条件：{filters} | pending |
| `backend:export.readme.personal` | This file contains personal data, such as researchers' names. Keep it within the office and delete copies you no longer need. | このファイルには研究者の氏名などの個人情報が含まれます。オフィス内で扱い、不要になった複製は削除してください。 | pending |
| `backend:export.readme.scope_all` | Rows: every release, {count} in all. | 対象：すべてのリリース（計 {count} 件） | pending |
| `backend:export.readme.scope_view` | Rows: the releases shown on the Data page, {count} in all. | 対象：データページに表示中のリリース（計 {count} 件） | pending |
| `backend:export.readme.search` | search for “{text}” | 「{text}」で検索 | pending |
| `backend:export.readme.separator` | ,  | 、 | pending |
| `backend:export.readme.state_empty` | Empty: not recorded yet, or not due yet. | 空欄：まだ記録されていないか、まだ期日前です。 | pending |
| `backend:export.readme.state_na` | N/A: the number can't exist for this release, such as Altmetric without a DOI. | 該当なし：このリリースには存在しない数値です（例：DOI のないリリースの Altmetric）。 | pending |
| `backend:export.readme.state_value` | A number was recorded. 0 is a real zero. | 数値：記録済みです。0 は実際にゼロだったことを示します。 | pending |
| `backend:export.readme.states_heading` | How to read the numbers | 数値の見方 | pending |
| `backend:export.readme.title` | Release Radar export | Release Radar エクスポート | pending |
| `backend:export.readme.view_all` | All | すべて | pending |
| `backend:export.readme.view_mine` | Mine | 自分の担当 | pending |
| `backend:export.readme.year` | Academic year: the year it begins in, so {year} runs from {first} to {last}. It comes from the release date. | 年度：その年度が始まる年の数字です。{year}年度は {first} から {last} までです。リリース日から求めています。 | pending |
| `backend:export.sheets.fields` | Fields | 分野 | pending |
| `backend:export.sheets.readme` | Read me | はじめにお読みください | pending |
| `backend:export.sheets.releases` | Releases | リリース | pending |
| `backend:export.sheets.units` | Units | 部局 | pending |
| `backend:export.unit_types.center` | Center | センター | pending |
| `backend:export.unit_types.institute` | Institute | 研究所 | pending |
| `backend:export.unit_types.other` | Other | その他 | pending |
| `backend:export.unit_types.school` | School | 研究科・学部 | pending |
| `backend:export.values.not_applicable` | N/A | 該当なし | pending |
| `frontend:data.open_hint` | Double-click a release, or press Shift+Enter, for the full record. | リリースをダブルクリックするか Shift+Enter を押すと、詳細を表示します。 | pending |
| `backend:export.fields.researcher_gender` | Researcher gender | 研究者の性別 | pending |
| `backend:export.genders.F` | Female | 女性 | pending |
| `backend:export.genders.M` | Male | 男性 | pending |
| `backend:export.genders.not_recorded` | Not recorded | 未記録 | pending |
| `backend:export.genders.other` | Other | その他 | pending |
| `backend:export.readme.code_year` | A release code keeps the year it was given, even if the date moved later. | リリースコードは付いたときの年度のままです。あとで日付が動いても変わりません。 | pending |
| `backend:export.readme.flags` | Yes-or-no columns, such as Embargoed: 1 means yes, 0 means no. | 「はい／いいえ」の列（エンバーゴありなど）：1 は「はい」、0 は「いいえ」を表します。 | pending |
| `backend:export.readme.academic_year` | AY{year} | {year}年度 | pending |
| `frontend:writers.caption` | Releases per writer and month in {{year}}, counted by release date. Click a name to see those releases on the Data page. | {{year}}のライター別・月別のリリース件数です（リリース日で集計）。名前をクリックすると、データページでそのリリースを表示します。 | pending |
| `frontend:writers.export_notice` | The file contains colleagues' names. Keep it within the office. | ファイルには同僚の氏名が含まれます。オフィス内で扱ってください。 | pending |
| `frontend:writers.export_title` | Export the counts | 件数をエクスポート | pending |
| `frontend:writers.export_xlsx` | Excel, with a Read me sheet | Excel（「はじめにお読みください」シート付き） | pending |
| `frontend:writers.inactive` | No longer active in the writers list | ライターの一覧で無効になっています | pending |
| `frontend:writers.no_writer` | No writer yet | ライター未設定 | pending |
| `frontend:writers.total` | Total | 合計 | pending |
| `frontend:writers.undated` | Not counted yet: releases without a release date ({{count}}). | まだ数えていないリリース：リリース日のないもの（{{count}} 件） | pending |
| `frontend:writers.writer` | Writer | ライター | pending |
| `frontend:writers.year` | Academic year | 年度 | pending |
| `backend:writers_export.no_writer` | No writer yet | ライター未設定 | pending |
| `backend:writers_export.readme.counting` | Each number counts releases by their release date. Releases without a release date, and removed releases, are not counted. | 各数値は、リリース日に基づくリリースの件数です。リリース日のないリリースと削除したリリースは数えていません。 | pending |
| `backend:writers_export.readme.personal` | This file contains colleagues' names. Keep it within the office. | このファイルには同僚の氏名が含まれます。オフィス内で扱ってください。 | pending |
| `backend:writers_export.readme.title` | Release Radar: releases per writer | Release Radar：ライター別のリリース件数 | pending |
| `backend:writers_export.readme.totals` | The last column and the last row are totals. | 最後の列と最後の行は合計です。 | pending |
| `backend:writers_export.readme.undated` | Not counted yet: {count} release(s) without a release date. | まだ数えていないリリース：リリース日のないものが {count} 件あります。 | pending |
| `backend:writers_export.readme.year` | Academic year {year}: {first} to {last}. | {year}年度：{first} から {last} まで | pending |
| `backend:writers_export.sheet` | Writers | ライター | pending |
| `backend:writers_export.total` | Total | 合計 | pending |
| `backend:writers_export.writer` | Writer | ライター | pending |
| `frontend:errors.gender_invalid` | Please enter female, male or other, or leave it empty if it isn't recorded. | 女性、男性、その他のいずれかを入力してください。記録がない場合は空欄にしてください。 | pending |
| `frontend:errors.gender_needs_researcher` | Choose the researcher first: the gender is theirs. | 先に研究者を選んでください。性別は研究者の情報です。 | pending |
| `frontend:release_fields.researcher_gender` | Researcher gender | 研究者の性別 | pending |
| `frontend:writers.all_years` | All years | すべての年度 | pending |
| `frontend:writers.caption_all` | Releases per writer and academic year, counted by release date. Click a name to see those releases on the Data page. | ライター別・年度別のリリース件数です（リリース日で集計）。名前をクリックすると、データページでそのリリースを表示します。 | pending |
| `backend:writers_export.readme.all_years` | All academic years, {first} to {last}. | すべての年度（{first}〜{last}） | pending |
| `frontend:errors.import_column_missing` | A column the import needs is missing. | インポートに必要な列がありません。 | pending |
| `frontend:errors.import_not_a_workbook` | That file can't be read as an Excel workbook (.xlsx). | このファイルは Excel ワークブック（.xlsx）として読み込めません。 | pending |
| `frontend:errors.import_owner_unknown` | A chosen owner is not a user here any more. Please choose again. | 選択した所有者はユーザーではなくなっています。もう一度選んでください。 | pending |
| `frontend:errors.import_sheet_missing` | A sheet the import needs is missing. | インポートに必要なシートがありません。 | pending |
| `frontend:settings.import.before_import` | Please read the report first. Import does exactly what was checked, in one go. | 先にレポートをお読みください。インポートは、確認した内容をそのまま一度に実行します。 | pending |
| `frontend:settings.import.check` | Check | 確認 | pending |
| `frontend:settings.import.check_again` | The files or owners changed since the check: check again first. | 確認の後にファイルまたは所有者が変わりました。先にもう一度確認してください。 | pending |
| `frontend:settings.import.checking` | Checking… | 確認しています… | pending |
| `frontend:settings.import.done` | Imported | インポートしました | pending |
| `frontend:settings.import.dry_run` | What an import would do (nothing has changed yet) | インポートした場合の結果（まだ何も変更していません） | pending |
| `frontend:settings.import.help` | Brings in the releases from the press-release workbook (sheet PR DATA), with the staff, units, fields and two-name releases from the intake workbook. Check first: a check changes nothing and lists everything worth a look. Importing again later finds each release by its code, updates it, and never empties anything. | プレスリリースのワークブック（PR DATA シート）のリリースを、インテーク用ワークブックのスタッフ、部局、分野、複数研究者のリリースとあわせて取り込みます。まず確認してください。確認では何も変更せず、確認が必要な点をすべて一覧にします。後でもう一度インポートすると、各リリースをコードで見つけて更新します。空欄で上書きすることはありません。 | pending |
| `frontend:settings.import.import` | Import | インポート | pending |
| `frontend:settings.import.importing` | Importing… | インポートしています… | pending |
| `frontend:settings.import.intake` | Intake workbook (.xlsx) | インテーク用ワークブック（.xlsx） | pending |
| `frontend:settings.import.levels` | To check: {{check}} · dashes and N/A: {{dash}} · changed on reading: {{info}} | 要確認：{{check}} · ダッシュと N/A：{{dash}} · 読み取り時の変換：{{info}} | pending |
| `frontend:settings.import.missing_column` | Missing column: {{column}}. | 列がありません：{{column}} | pending |
| `frontend:settings.import.missing_sheet` | Missing sheet: {{sheet}}. | シートがありません：{{sheet}} | pending |
| `frontend:settings.import.not_imported` | Not imported | 取り込まない | pending |
| `frontend:settings.import.owners` | Whose are the personal fields in the workbook? | ワークブックの個人項目は誰のものですか？ | pending |
| `frontend:settings.import.owners_help` | Each becomes that person's own field, with the workbook's values. Leave one as it is to skip it; importing again later adds it. | それぞれ、その人の個人項目としてワークブックの値とともに作成します。取り込まない項目はそのままにしてください。後でもう一度インポートすると追加できます。 | pending |
| `frontend:settings.import.release_list` | Press-release workbook (.xlsx) | プレスリリースのワークブック（.xlsx） | pending |
| `frontend:settings.import.report_csv` | Report (CSV) | レポート（CSV） | pending |
| `frontend:settings.import.report_md` | Report (Markdown) | レポート（Markdown） | pending |
| `frontend:settings.import.takes_time` | Each DOI is looked up at Crossref: about half a minute. | 各 DOI を Crossref で調べるため、30 秒ほどかかります。 | pending |
| `backend:import.columns.code` | Code | コード | pending |
| `backend:import.columns.column` | Column | 列 | pending |
| `backend:import.columns.level` | Kind | 種類 | pending |
| `backend:import.columns.outcome` | What happened | 結果 | pending |
| `backend:import.columns.row` | Row | 行 | pending |
| `backend:import.columns.value` | In the workbook | ワークブックの値 | pending |
| `backend:import.counts.crossref_found` | Papers found at Crossref | Crossref で見つかった論文 | pending |
| `backend:import.counts.crossref_not_found` | DOIs Crossref doesn't know | Crossref にない DOI | pending |
| `backend:import.counts.crossref_unavailable` | DOIs Crossref didn't answer for | Crossref から応答のなかった DOI | pending |
| `backend:import.counts.dashes` | Numbers marked not applicable by a dash | ダッシュで該当なしとした数値 | pending |
| `backend:import.counts.fields_new` | New fields | 新しい分野 | pending |
| `backend:import.counts.personal_fields_new` | New personal fields | 新しい個人項目 | pending |
| `backend:import.counts.releases_in_workbook` | Rows in the workbook | ワークブックの行数 | pending |
| `backend:import.counts.releases_new` | New releases | 新しいリリース | pending |
| `backend:import.counts.releases_skipped` | Rows not imported | インポートしなかった行 | pending |
| `backend:import.counts.releases_unchanged` | Releases already up to date | すでに最新のリリース | pending |
| `backend:import.counts.releases_updated` | Releases updated | 更新したリリース | pending |
| `backend:import.counts.researchers_incomplete` | New researchers marked incomplete | 「不完全」とした新しい研究者 | pending |
| `backend:import.counts.researchers_linked` | Researchers found already in Release Radar | Release Radar にすでにいた研究者 | pending |
| `backend:import.counts.researchers_new` | New researchers | 新しい研究者 | pending |
| `backend:import.counts.trimmed` | Cells tidied (spaces, line breaks) | 整えたセル（空白、改行） | pending |
| `backend:import.counts.units_new` | New units | 新しい部局 | pending |
| `backend:import.counts.values` | Numbers imported | 取り込んだ数値 | pending |
| `backend:import.counts.website_off_domain` | Releases whose website views don't apply | ウェブサイト閲覧数が該当なしのリリース | pending |
| `backend:import.counts.writers_linked` | Writers linked to their account | アカウントに紐づけたライター | pending |
| `backend:import.counts.writers_new` | New writers | 新しいライター | pending |
| `backend:import.levels.check` | Please check | 要確認 | pending |
| `backend:import.levels.dash` | Dash or N/A | ダッシュまたは N/A | pending |
| `backend:import.levels.info` | Changed on reading | 読み取り時の変換 | pending |
| `backend:import.md.made` | {when}, by {who}. | {when}、{who} | pending |
| `backend:import.md.none` | Nothing. | ありません。 | pending |
| `backend:import.md.section_check` | Please check | 要確認 | pending |
| `backend:import.md.section_dash` | Dashes and N/A (the dash rule) | ダッシュと N/A（ダッシュのルール） | pending |
| `backend:import.md.section_info` | Changed on reading | 読み取り時の変換 | pending |
| `backend:import.md.summary` | Summary | 概要 | pending |
| `backend:import.md.title_commit` | Workbook import | ワークブックのインポート | pending |
| `backend:import.md.title_dry_run` | Workbook import: dry run (nothing changed) | ワークブックのインポート：試行（変更なし） | pending |
| `backend:import.report.code_duplicate` | Row {first} has this code too: this release gets {new}. | {first} 行目にも同じコードがあります。このリリースには {new} を付けました。 | pending |
| `backend:import.report.code_year_differs` | The release date falls in AY{year}: the code keeps its own year (D35). | リリース日は {year}年度ですが、コードは付いたときの年度のままです（D35）。 | pending |
| `backend:import.report.crossref_not_found` | Crossref does not know this DOI: the paper's journal, date and authors stay empty. | Crossref にこの DOI がありません。論文の掲載誌、発表日、著者は空欄のままです。 | pending |
| `backend:import.report.crossref_unavailable` | Crossref did not answer: the paper's details stay empty. Import again later to fill them. | Crossref から応答がありませんでした。論文の情報は空欄のままです。後でもう一度インポートすると入力されます。 | pending |
| `backend:import.report.dash_empty` | Means none: left empty. | 「なし」の意味として空欄にしました。 | pending |
| `backend:import.report.dash_na` | Means not applicable (the dash rule). | 「該当なし」としました（ダッシュのルール）。 | pending |
| `backend:import.report.dash_not_embargoed` | Means not embargoed. | エンバーゴなしとしました。 | pending |
| `backend:import.report.date_from_text` | Read as {date}. | {date} と読みました。 | pending |
| `backend:import.report.doi_invalid` | Not a DOI: left empty. | DOI ではないため、空欄にしました。 | pending |
| `backend:import.report.doi_normalised` | Read as {doi}. | {doi} と読みました。 | pending |
| `backend:import.report.ea_url_unusual` | Not a EurekAlert news-release link: kept, and marked on the release. | EurekAlert のニュースリリースのリンクではありません。そのまま残し、リリースに印を付けました。 | pending |
| `backend:import.report.embargo_unreadable` | Neither a date nor a dash: left as it was. | 日付でもダッシュでもないため、変更していません。 | pending |
| `backend:import.report.gender_conflict` | This researcher's gender is recorded differently on another release: {kept} was kept. | この研究者の性別は、別のリリースで異なる記録になっています。{kept} のままにしました。 | pending |
| `backend:import.report.gender_dash` | Means not recorded. | 未記録としました。 | pending |
| `backend:import.report.gender_unreadable` | Not M or F: gender not recorded. | M でも F でもないため、性別は未記録です。 | pending |
| `backend:import.report.no_release_date` | No release date: imported without one, so its numbers are not due yet. | リリース日がないまま取り込みました。数値の入力時期はまだ来ていません。 | pending |
| `backend:import.report.not_a_date` | Not a date: left empty. | 日付ではないため、空欄にしました。 | pending |
| `backend:import.report.not_a_number` | Not a number: left as missing. | 数値ではないため、未入力のままです。 | pending |
| `backend:import.report.number_from_text` | Text read as the number {number}. | 文字列を数値 {number} と読みました。 | pending |
| `backend:import.report.number_shown_as_date` | A date in a number column, probably the number {number} formatted as a date: left as missing. Type the number in if that's right. | 数値の列に日付があります。おそらく数値 {number} が日付の書式で表示されたものです。未入力のままにしました。正しければ数値を入力してください。 | pending |
| `backend:import.report.personal_field_skipped` | No owner chosen for this personal field: its values were not imported. | この個人項目の所有者が選ばれていないため、値はインポートしていません。 | pending |
| `backend:import.report.release_made_in_app` | A release made in the app already has this code: the workbook's values go into it. | アプリで作成したリリースに同じコードがあります。ワークブックの値をそのリリースに入れます。 | pending |
| `backend:import.report.release_restored` | This release had been removed in the app: it is back. | このリリースはアプリで削除されていましたが、元に戻しました。 | pending |
| `backend:import.report.researcher_first_listed` | Several names: {name}, the first, is the corresponding researcher; the others went to Also featured. | 複数の氏名があります。最初の {name} を対応研究者とし、ほかは「その他の掲載者」に入れました。 | pending |
| `backend:import.report.researcher_from_sheet` | Taken from the Two-name releases sheet: {name}. | Two-name releases シートから {name} を採用しました。 | pending |
| `backend:import.report.researcher_missing` | No researcher. | 研究者の記載がありません。 | pending |
| `backend:import.report.researcher_resolved` | Surname only: read as {name}, the one author of the paper with this family name. Marked unverified. | 姓のみの記載です。論文の著者のうちこの姓を持つ唯一の人物として {name} と読みました。「未確認」としています。 | pending |
| `backend:import.report.researcher_unresolved` | Surname only, and the paper's authors don't settle it ({matches} with this family name): kept as written, marked incomplete. | 姓のみの記載で、論文の著者からは特定できません（この姓の著者：{matches} 人）。記載のまま「不完全」としています。 | pending |
| `backend:import.report.skipped_no_code` | No usable code: not imported. | 使えるコードがないため、インポートしていません。 | pending |
| `backend:import.report.skipped_no_title` | No title and no DOI: not imported. | タイトルも DOI もないため、インポートしていません。 | pending |
| `backend:import.report.skipped_unit_writer` | Written by a unit, not by the office: not imported. | 部局が執筆したリリースで、オフィスの担当ではないため、インポートしていません。 | pending |
| `backend:import.report.time_from_text` | Read as {time}. | {time} と読みました。 | pending |
| `backend:import.report.time_unreadable` | Not a time: left empty. | 時刻ではないため、空欄にしました。 | pending |
| `backend:import.report.top_page` | On the EurekAlert top page (place {place}). | EurekAlert のトップページ掲載（{place} 番目）。 | pending |
| `backend:import.report.unit_alias` | Read as the unit {unit}. | 部局 {unit} と読みました。 | pending |
| `backend:import.report.unit_unknown` | Not in the Units sheet: left without a unit. | Units シートにないため、部局は空欄です。 | pending |
| `backend:import.report.value_where_na` | A number where the rules say there can't be one: kept. | ルール上は存在しないはずの数値があります。そのまま残しました。 | pending |
| `backend:import.report.website_off_domain` | Not on {domain}: website views don't apply to this release. | {domain} 上にないため、このリリースのウェブサイト閲覧数は該当なしです。 | pending |
| `backend:import.report.writer_unknown` | Not in the Staff sheet: left without a writer. | Staff シートにないため、ライターは空欄です。 | pending |
| `backend:import.report.writer_without_account` | Writes releases but has no account with this email yet: the writer is not linked to a user. Invite them in Settings → Users and import again to link. | リリースを担当していますが、このメールアドレスのアカウントがまだありません。ライターはユーザーに紐づいていません。設定 → ユーザーで招待してから、もう一度インポートすると紐づきます。 | pending |
| `frontend:data.filters.no_writer` | No writer yet | ライター未設定 | pending |
| `frontend:settings.import.history` | Checks and imports so far | これまでの確認とインポート | pending |
| `frontend:settings.import.history_counts` | {{new}} new, {{updated}} updated, {{check}} to check | 新規 {{new}} 件、更新 {{updated}} 件、要確認 {{check}} 件 | pending |
| `frontend:settings.import.history_report` | Report | レポート | pending |
| `frontend:settings.import.history_result` | Result | 結果 | pending |
| `frontend:settings.import.history_what` | What | 種類 | pending |
| `frontend:settings.import.history_when` | When | 日時 | pending |
| `frontend:settings.import.history_who` | Who | 実行者 | pending |
| `frontend:settings.import.kind_check` | Check | 確認 | pending |
| `frontend:settings.import.kind_import` | Import | インポート | pending |
| `backend:export.readme.no_writer` | no writer yet | ライター未設定 | pending |
| `frontend:data.filters.any_release_type` | Any type | すべての種類 | pending |
| `frontend:data.filters.no_release_type` | No type | 種類未設定 | pending |
| `frontend:data.filters.release_type` | Release type | リリースの種類 | pending |
| `frontend:data.grid_keys` | Arrow keys move between cells. Type to replace a cell, or press Enter to change it. Shift+Enter opens the full record, and Cmd or Ctrl+Enter opens a link. From the first row, the up arrow reaches the column headings, where Enter sorts. | 矢印キーでセル間を移動します。入力するとセルの値を置き換え、Enter キーで編集します。Shift+Enter で詳細を、Cmd または Ctrl+Enter でリンクを開きます。先頭の行で上矢印キーを押すと列見出しに移動し、Enter キーで並べ替えます。 | pending |
| `frontend:manual.contents` | On this page | このページの内容 | pending |
| `frontend:release_fields.release_type` | Release type | リリースの種類 | pending |
| `frontend:settings.lists.add_release_type` | Add a type | 種類を追加 | pending |
| `frontend:settings.lists.default_release_type` | New releases start as | 新しいリリースの既定の種類 | pending |
| `frontend:settings.lists.default_release_type_hint` | Imported releases too. Anyone can change a release's type afterwards. | インポートしたリリースにも適用されます。種類は後からいつでも変更できます。 | pending |
| `frontend:settings.lists.kinds.release_types` | Release types | リリースの種類 | pending |
| `frontend:settings.lists.no_default_release_type` | No type | 種類なし | pending |
| `frontend:settings.lists.position` | Order | 順番 | pending |
| `frontend:settings.lists.release_types_help` | What kind of release it is, after EurekAlert's categories. Analysis will keep the types apart, so each release should have the right one. | EurekAlert の分類に沿った、リリースの種類です。分析では種類ごとに分けて扱うため、各リリースに正しい種類を設定してください。 | pending |
| `backend:export.fields.release_type` | Release type | リリースの種類 | pending |
| `backend:export.readme.no_release_type` | No release type | 種類なし | pending |
| `backend:seed.release_type.article_highlight` | Article highlight | 論文ハイライト | pending |
| `backend:seed.release_type.book` | Book announcement | 書籍の発表 | pending |
| `backend:seed.release_type.business` | Business announcement | ビジネスに関する発表 | pending |
| `backend:seed.release_type.feature` | Feature story | 特集記事 | pending |
| `backend:seed.release_type.grant_award` | Grant and award announcement | 助成・受賞の発表 | pending |
| `backend:seed.release_type.media_advisory` | Media advisory | 取材案内 | pending |
| `backend:seed.release_type.meeting` | Meeting announcement | 会議の告知 | pending |
| `backend:seed.release_type.multimedia` | Multimedia release | マルチメディアリリース | pending |
| `backend:seed.release_type.peer_reviewed` | Peer-reviewed publication | 査読付き論文 | pending |
| `backend:seed.release_type.press_summary` | Press summary | プレスサマリー | pending |
| `backend:seed.release_type.reports_proceedings` | Reports and proceedings | 報告書・会議録 | pending |
| `frontend:data.open` | Open | 開く | pending |
| `frontend:data.open_link` | Open the {{field}} in a new tab | {{field}}を新しいタブで開く | pending |
| `frontend:data.from_ga4` | from Google Analytics | Google Analytics から取得 | pending |
| `frontend:data.typed_over_ga4` | entered by hand, so fetching leaves it alone | 手入力のため、自動取得では変更しません | pending |
| `frontend:errors.ga4_key_bad_private_key` | The private key in that file can't be read. Download a new key. | ファイル内の秘密鍵を読み取れません。新しいキーをダウンロードしてください。 | pending |
| `frontend:errors.ga4_key_incomplete` | That key file is missing its address or private key. Download a new key. | キーファイルにアドレスまたは秘密鍵がありません。新しいキーをダウンロードしてください。 | pending |
| `frontend:errors.ga4_key_not_json` | That file isn't a JSON key. Choose the .json file Google Cloud downloaded. | JSON 形式のキーではありません。Google Cloud でダウンロードした .json ファイルを選んでください。 | pending |
| `frontend:errors.ga4_key_not_service_account` | That file isn't a service-account key. In Google Cloud, create the key under IAM & Admin → Service accounts → Keys. | サービスアカウントのキーではありません。Google Cloud の IAM と管理 → サービスアカウント → キー で作成してください。 | pending |
| `frontend:errors.ga4_key_unreadable` | The stored key cannot be read on this install; choose the key file again. | 保存されているキーは、この環境では読み取れません。キーファイルをもう一度選んでください。 | pending |
| `frontend:errors.ga4_no_key` | Choose the key file first. | 先にキーファイルを選んでください。 | pending |
| `frontend:errors.ga4_no_property` | Enter the property ID first. | 先にプロパティ ID を入力してください。 | pending |
| `frontend:errors.ga4_property_digits` | A property ID is digits only, for example 123456789. The G-… code is a measurement ID, not the property ID. | プロパティ ID は数字のみです（例：123456789）。G- で始まるコードは測定 ID で、プロパティ ID ではありません。 | pending |
| `frontend:settings.data.jobs.ga4-website-views` | Website views (daily) | ウェブサイトの閲覧数（毎日） | pending |
| `frontend:settings.data.jobs.ga4-website-views-manual` | Website views (Fetch now) | ウェブサイトの閲覧数（今すぐ取得） | pending |
| `frontend:settings.help.integrations` | Connections to outside services. Keys are stored encrypted and never shown again. | 外部サービスとの連携です。キーは暗号化して保存し、二度と表示しません。 | pending |
| `frontend:settings.integrations.ga4.code` | Code | コード | pending |
| `frontend:settings.integrations.ga4.connected_as` | Key stored for {{email}}. | {{email}} のキーを保存済みです。 | pending |
| `frontend:settings.integrations.ga4.connected_as_project` | Key stored for {{email}} (Google Cloud project {{project}}). | {{email}} のキーを保存済みです（Google Cloud プロジェクト {{project}}）。 | pending |
| `frontend:settings.integrations.ga4.counts` | Releases | リリース | pending |
| `frontend:settings.integrations.ga4.counts_text` | {{fetched}} with website views from Google Analytics, {{waiting}} still waiting, {{open}} within their 28 days. | Google Analytics の閲覧数あり {{fetched}} 件、取得待ち {{waiting}} 件、28 日間の期間中 {{open}} 件。 | pending |
| `frontend:settings.integrations.ga4.fetch_now` | Fetch now | 今すぐ取得 | pending |
| `frontend:settings.integrations.ga4.fetch_started` | Fetching website views. This page shows the result when it's done. | ウェブサイトの閲覧数を取得しています。完了するとこのページに結果が表示されます。 | pending |
| `frontend:settings.integrations.ga4.google_said` | Google's message: {{detail}} | Google からのメッセージ：{{detail}} | pending |
| `frontend:settings.integrations.ga4.help` | Website views come from Google Analytics: each release's page on {{domain}}, counted over its first 28 days. Every day after the nightly backup, Release Radar fetches the releases whose 28 days and 2 days' processing have passed. | ウェブサイトの閲覧数は Google Analytics から取得します。{{domain}} 上の各リリースのページについて、リリース日から 28 日間の閲覧数です。毎日、夜間バックアップの後に、28 日間と処理期間の 2 日間が過ぎたリリースの数値を取得します。 | pending |
| `frontend:settings.integrations.ga4.help_no_domain` | Website views come from Google Analytics. Set your news website in Settings → Institution first: only releases on it have website views. | ウェブサイトの閲覧数は Google Analytics から取得します。先に 設定 → 機関情報 でニュースサイトを設定してください。閲覧数はそのサイト上のリリースにのみ適用されます。 | pending |
| `frontend:settings.integrations.ga4.key_choose` | Service-account key (JSON file) | サービスアカウントのキー（JSON ファイル） | pending |
| `frontend:settings.integrations.ga4.key_hint` | The file Google Cloud downloaded. It is stored encrypted and never shown again. Afterwards, keep it in the password manager and delete the downloaded copy. | Google Cloud でダウンロードしたファイルです。暗号化して保存し、二度と表示しません。保存後はパスワードマネージャーに保管し、ダウンロードしたファイルは削除してください。 | pending |
| `frontend:settings.integrations.ga4.key_removed` | Key removed. | キーを削除しました。 | pending |
| `frontend:settings.integrations.ga4.key_replace` | Replace the key (JSON file) | キーを差し替える（JSON ファイル） | pending |
| `frontend:settings.integrations.ga4.key_saved` | Key stored. | キーを保存しました。 | pending |
| `frontend:settings.integrations.ga4.key_unreadable` | The stored key cannot be read on this install; enter it again. | 保存されているキーは、この環境では読み取れません。もう一度入力してください。 | pending |
| `frontend:settings.integrations.ga4.last_run` | Last fetch | 前回の取得 | pending |
| `frontend:settings.integrations.ga4.last_tested` | Last tested {{when}}. | 最終テスト：{{when}} | pending |
| `frontend:settings.integrations.ga4.manual` | How to connect it, step by step | 接続の手順 | pending |
| `frontend:settings.integrations.ga4.manual_heading` | Connect Google Analytics | Google Analytics に接続する | pending |
| `frontend:settings.integrations.ga4.never_run` | Not yet | まだありません | pending |
| `frontend:settings.integrations.ga4.not_connected` | Not connected yet. | まだ接続されていません。 | pending |
| `frontend:settings.integrations.ga4.page` | Page | ページ | pending |
| `frontend:settings.integrations.ga4.property` | Property ID | プロパティ ID | pending |
| `frontend:settings.integrations.ga4.property_hint` | Digits only: Google Analytics → Admin → Property details. | 数字のみ：Google Analytics → 管理 → プロパティの詳細 | pending |
| `frontend:settings.integrations.ga4.release` | Release | リリース | pending |
| `frontend:settings.integrations.ga4.release_date` | Release date | リリース日 | pending |
| `frontend:settings.integrations.ga4.remove_key` | Remove key | キーを削除 | pending |
| `frontend:settings.integrations.ga4.remove_question` | Remove the key? Website views already fetched stay. | キーを削除しますか？取得済みの閲覧数は残ります。 | pending |
| `frontend:settings.integrations.ga4.running` | Fetching now… | 取得中… | pending |
| `frontend:settings.integrations.ga4.schedule` | Fetching | 取得 | pending |
| `frontend:settings.integrations.ga4.schedule_daily` | Every day, after the nightly backup. First fetched {{when}}. | 毎日、夜間バックアップの後に取得します。初回取得：{{when}} | pending |
| `frontend:settings.integrations.ga4.schedule_waiting` | Daily fetches start after the first Fetch now. The first one fetches every release since the new website went live. | 毎日の取得は、最初に「今すぐ取得」を実行した後に始まります。最初の取得では、新しいウェブサイトの公開以降のすべてのリリースを取得します。 | pending |
| `frontend:settings.integrations.ga4.test.api_disabled` | The Google Analytics Data API is not enabled in this key's Google Cloud project. Enable it under APIs & Services → Library, then test again. | このキーの Google Cloud プロジェクトで Google Analytics Data API が有効になっていません。API とサービス → ライブラリ で有効にしてから、もう一度テストしてください。 | pending |
| `frontend:settings.integrations.ga4.test.connected` | Connected. Google Analytics counted {{views}} page views on {{host}} on {{date}}. | 接続できました。{{date}} の {{host}} のページビューは {{views}} 件です。 | pending |
| `frontend:settings.integrations.ga4.test.connected_any_host` | Connected. Google Analytics counted {{views}} page views on {{date}}. | 接続できました。{{date}} のページビューは {{views}} 件です。 | pending |
| `frontend:settings.integrations.ga4.test.connected_no_views` | Connected, but Google Analytics counted no page views on {{host}} on {{date}}. Check that this property is the one for {{host}}. | 接続できましたが、{{date}} の {{host}} のページビューは 0 件でした。このプロパティが {{host}} のものか確認してください。 | pending |
| `frontend:settings.integrations.ga4.test.google_error` | Google Analytics answered with an error. | Google Analytics からエラーが返されました。 | pending |
| `frontend:settings.integrations.ga4.test.key_rejected` | Google refused the key. It may have been deleted or disabled in Google Cloud: create a new key and choose it here. | Google がキーを拒否しました。Google Cloud で削除または無効化された可能性があります。新しいキーを作成して、ここで選択してください。 | pending |
| `frontend:settings.integrations.ga4.test.no_access` | The service account has no access to this property. In Google Analytics → Admin → Property access management, add its address as Viewer, and check the property ID. | サービスアカウントにこのプロパティへのアクセス権がありません。Google Analytics → 管理 → プロパティのアクセス管理 で、そのアドレスを閲覧者として追加し、プロパティ ID も確認してください。 | pending |
| `frontend:settings.integrations.ga4.test.quota` | Google Analytics' quota for this property is used up for now. Try again in an hour. | このプロパティの Google Analytics の割り当て量を使い切りました。1 時間後にもう一度お試しください。 | pending |
| `frontend:settings.integrations.ga4.test.unreachable` | Google could not be reached. Check the internet connection of the computer Release Radar runs on. | Google に接続できませんでした。Release Radar を動かしているコンピューターのインターネット接続を確認してください。 | pending |
| `frontend:settings.integrations.ga4.test.wrong_property` | Google Analytics does not accept this property ID. It is digits only, under Admin → Property details. | Google Analytics がこのプロパティ ID を受け付けません。管理 → プロパティの詳細 にある数字のみの ID です。 | pending |
| `frontend:settings.integrations.ga4.test_button` | Test connection | 接続をテスト | pending |
| `frontend:settings.integrations.ga4.testing` | Testing… | テスト中… | pending |
| `frontend:settings.integrations.ga4.title` | Google Analytics | Google Analytics | pending |
| `frontend:settings.integrations.ga4.views_title` | Website views | ウェブサイトの閲覧数 | pending |
| `frontend:settings.integrations.ga4.waiting_help` | Their 28 days and 2 days' processing have passed, yet they have no website views. After a fetch, this means Google Analytics has no data for the page's address: check it in the record. A number entered by hand in the record always counts instead. | 28 日間と処理期間の 2 日間が過ぎましたが、閲覧数がありません。取得後もここに残る場合、そのページのアドレスについて Google Analytics にデータがありません。詳細画面でアドレスを確認してください。詳細画面で手入力した数値は、常に優先されます。 | pending |
| `frontend:settings.integrations.ga4.waiting_help_before` | Their 28 days and 2 days' processing have passed. Fetch now fetches them. | 28 日間と処理期間の 2 日間が過ぎています。「今すぐ取得」で取得します。 | pending |
| `frontend:settings.integrations.ga4.waiting_title` | Still without website views | 閲覧数がまだないリリース | pending |
| `backend:export.inferred_column` | {label} inferred | {label}（推定） | pending |
| `backend:export.readme.state_inferred` | Inferred: where a column ending in “inferred” holds 1, the 0 before it was not entered. The paper was published on or after the release date, so it could have no Altmetric score before the release. | 推定：「（推定）」で終わる列が 1 の場合、その前の列の 0 は入力された値ではありません。論文の公開日がリリース日以降のため、リリース前に Altmetric スコアはあり得ません。 | pending |
| `frontend:data.inferred` | inferred | 推定 | pending |
| `frontend:data.inferred_state` | Inferred 0: the paper was published on or after the release date, so it had no Altmetric score before the release. A number typed here replaces it. | 推定の 0：論文の公開日がリリース日以降のため、リリース前の Altmetric スコアはありません。ここに数値を入力すると置き換わります。 | pending |
| `frontend:data.inferred_why` | Inferred 0: the paper was published on or after the release date, so it had no Altmetric score before the release. Type a number to replace it. | 推定の 0：論文の公開日がリリース日以降のため、リリース前の Altmetric スコアはありません。数値を入力すると置き換わります。 | pending |
| `frontend:data.feedback.activities` | Activities | 活動 | pending |
| `frontend:data.feedback.comments` | Comments | コメント | pending |
| `frontend:data.feedback.imported` | imported from {{template}} | {{template}} からインポート | pending |
| `frontend:data.feedback.inquiries` | Inquiries | 問い合わせ | pending |
| `frontend:data.feedback.language_en` | English | 英語 | pending |
| `frontend:data.feedback.language_ja` | Japanese | 日本語 | pending |
| `frontend:data.feedback.no_responses` | No feedback yet. | まだ回答はありません。 | pending |
| `frontend:data.feedback.none` | None | なし | pending |
| `frontend:data.feedback.not_answered` | Not answered | 未回答 | pending |
| `frontend:data.feedback.other` | Other: {{text}} | その他：{{text}} | pending |
| `frontend:data.feedback.scale` | {{word}} ({{score}}) | {{word}}（{{score}}） | pending |
| `frontend:data.feedback.scale_1` | Strongly disagree | まったくそう思わない | pending |
| `frontend:data.feedback.scale_2` | Disagree | そう思わない | pending |
| `frontend:data.feedback.scale_3` | Neither agree nor disagree | どちらともいえない | pending |
| `frontend:data.feedback.scale_4` | Agree | そう思う | pending |
| `frontend:data.feedback.scale_5` | Strongly agree | 強くそう思う | pending |
| `frontend:data.feedback.title` | Researcher feedback | 研究者アンケート | pending |
| `frontend:settings.data.feedback_title` | Import researcher feedback | 研究者アンケートをインポートする | pending |
| `frontend:settings.feedback.check_again` | The file changed since the check: check again first. | 確認の後にファイルが変わりました。もう一度確認してください。 | pending |
| `frontend:settings.feedback.file` | Microsoft Forms export (.xlsx) | Microsoft Forms のエクスポート（.xlsx） | pending |
| `frontend:settings.feedback.help` | Brings in the researchers' answers from the Microsoft Forms survey: export the responses (Open results in Excel) and choose that file. Each response is linked to its release by the press release ID. Check first: a check changes nothing and lists what is worth a look. Importing a newer export later adds only the new responses. | Microsoft Forms のアンケートの研究者の回答を取り込みます。回答をエクスポートし（Excel で結果を開く）、そのファイルを選んでください。各回答は、プレスリリース ID でリリースに紐付けます。まず確認してください。確認では何も変更せず、確認が必要な点を一覧にします。後から新しいエクスポートをインポートすると、新しい回答だけが追加されます。 | pending |
| `frontend:settings.feedback.history_counts` | {{new}} new, {{already}} already imported, {{check}} to check | 新規 {{new}} 件、インポート済み {{already}} 件、要確認 {{check}} 件 | pending |
| `frontend:settings.feedback.levels` | To check: {{check}} · noted on reading: {{info}} | 確認が必要：{{check}} ・ 読み取り時の記録：{{info}} | pending |
| `backend:import.counts.feedback_already` | Responses already imported, left as they are | インポート済みの回答（変更なし） | pending |
| `backend:import.counts.feedback_corrected` | Inverted scales corrected | 逆向きの評価を修正した回答 | pending |
| `backend:import.counts.feedback_linked` | New responses linked to their release | リリースに紐付けた新しい回答 | pending |
| `backend:import.counts.feedback_new` | New responses | 新しい回答 | pending |
| `backend:import.counts.feedback_not_linked` | New responses without a release | リリースのない新しい回答 | pending |
| `backend:import.counts.feedback_other_texts` | Answers written in “Other” | 「その他」に記入された回答 | pending |
| `backend:import.counts.feedback_releases` | Releases with feedback | アンケート回答のあるリリース | pending |
| `backend:import.counts.feedback_rows` | Responses in the file | ファイル内の回答 | pending |
| `backend:import.counts.feedback_skipped` | Rows not imported (test responses) | インポートしなかった行（テスト回答） | pending |
| `backend:import.md.feedback_title_commit` | Researcher feedback import | 研究者アンケートのインポート | pending |
| `backend:import.md.feedback_title_dry_run` | Researcher feedback import: dry run (nothing changed) | 研究者アンケートのインポート：確認（変更なし） | pending |
| `backend:import.report.feedback_all_disagree` | All three statements are “Strongly disagree” (response {id}). An inverted scale, as with four earlier responses? Not corrected: please check. | 3 項目すべてが「まったくそう思わない」です（回答 {id}）。以前の 4 件と同じく評価の逆転かもしれません。修正していないので、確認してください。 | pending |
| `backend:import.report.feedback_column_by_content` | Read as {what}, by its content: its heading says nothing. | 見出しに手がかりがないため、内容から {what} として読み取りました。 | pending |
| `backend:import.report.feedback_column_by_heading` | Read as {what}, by its heading. | 見出しから {what} として読み取りました。 | pending |
| `backend:import.report.feedback_column_ignored` | Not used ({what}). | 使用しません（{what}）。 | pending |
| `backend:import.report.feedback_corrected` | All three statements were “Strongly disagree”: corrected to “Strongly agree” (inverted scale, response {id}). The response's history shows both. | 3 項目すべてが「まったくそう思わない」でした。「強くそう思う」に修正しました（評価の逆転、回答 {id}）。回答の履歴に両方が残ります。 | pending |
| `backend:import.report.feedback_correction_not_needed` | Response {id} was to be corrected for an inverted scale, but its statements are not all “Strongly disagree”: left as given. Please check. | 回答 {id} は評価の逆転として修正する予定でしたが、すべてが「まったくそう思わない」ではないため、そのままにしました。確認してください。 | pending |
| `backend:import.report.feedback_language_unknown` | Unknown language: left empty. | 言語が不明のため、空欄にします。 | pending |
| `backend:import.report.feedback_linked_by_url` | Linked to the release with this EurekAlert link. | この EurekAlert のリンクを持つリリースに紐付けました。 | pending |
| `backend:import.report.feedback_none_with_others` | “None” ticked together with other answers ({question}): kept as given. | 「なし」がほかの回答と一緒に選ばれています（{question}）：そのまま保存します。 | pending |
| `backend:import.report.feedback_not_linked` | No release has this ID: the response is kept without a release. | この ID のリリースがありません。回答はリリースなしで保存します。 | pending |
| `backend:import.report.feedback_other_text` | Written in “Other” ({question}): kept as text on the response. | 「その他」に記入（{question}）：回答にテキストとして保存します。 | pending |
| `backend:import.report.feedback_reference_read_as` | Read as {release}. | {release} として読み取りました。 | pending |
| `backend:import.report.feedback_release_removed` | The release was removed in the app: the response is linked to it anyway. | このリリースはアプリで削除されていますが、回答は紐付けました。 | pending |
| `backend:import.report.feedback_scale_unknown` | Not a point on the agreement scale: this statement is left unanswered. | 評価の選択肢にない値のため、この項目は未回答とします。 | pending |
| `backend:import.report.feedback_skipped_staff_test` | The office's own test response: not imported. | 事務局のテスト回答のため、インポートしません。 | pending |
| `frontend:settings.import.fill_empty_only` | Only fill what is empty | 空欄のみ入力する | pending |
| `frontend:settings.import.fill_empty_only_help` | For bringing in what the team still entered in Excel. Releases already here get only what is empty or missing in Release Radar: no value, N/A, researcher, release type or removed release changes. New codes are added in full. The report lists every cell filled and every difference left alone. | Excel に引き続き入力された内容を取り込むためのものです。既存のリリースには、Release Radar で空欄または未入力の項目だけを入力します。値、該当なし、研究者、リリースの種類、削除したリリースは変更しません。新しいコードのリリースはすべて取り込みます。レポートには、入力したセルと、異なるがそのままにしたセルがすべて表示されます。 | pending |
| `backend:import.counts.cells_filled` | Cells filled because they were empty in Release Radar | Release Radar で空欄だったため入力したセル | pending |
| `backend:import.counts.cells_kept` | Cells where the workbook differs, left as they are | ワークブックと異なるが、そのままにしたセル | pending |
| `backend:import.report.fill_filled` | Empty in Release Radar ({field}): filled with the workbook's value. | Release Radar では空欄（{field}）：ワークブックの値を入力しました。 | pending |
| `backend:import.report.fill_kept` | Release Radar has “{current}” ({field}): kept, as only empty cells are filled. | Release Radar の値は「{current}」（{field}）：空欄のみ入力するため、そのままにしました。 | pending |
| `backend:import.report.fill_mode` | Only what is empty in Release Radar is filled: nothing already there changes. New codes are added in full. | Release Radar で空欄の項目だけを入力します。入力済みの内容は変更しません。新しいコードのリリースはすべて取り込みます。 | pending |
| `backend:import.report.fill_removed_left` | Removed in the app: left as it is, as only empty cells are filled. | アプリで削除されたリリースです。空欄のみ入力するため、そのままにしました。 | pending |
| `frontend:errors.profile_component_not_in_default` | Satisfaction and research outcomes never go into the default profile. Duplicate it to make one that includes them. | 満足度と研究上の成果は、既定のプロファイルには入れられません。複製して、それらを含むプロファイルを作成してください。 | pending |
| `frontend:errors.profile_component_unknown` | One of the components does not exist (any more). Reload the page. | 存在しない要素が含まれています。ページを再読み込みしてください。 | pending |
| `frontend:errors.profile_weights_total` | The weights must add up to 100. | 重みの合計を 100 にしてください。 | pending |
| `frontend:errors.shown_outside_analysed` | A shown type must also be analysed. | 表示する種類は、分析対象にも含める必要があります。 | pending |
| `frontend:settings.help.score_profiles` | How a release's score is made: its percentile in each component, weighted. Every save is a new version, and the old ones stay readable. | リリースのスコアの算出方法です。各要素のパーセンタイルに重みを付けて合計します。保存するたびに新しいバージョンとなり、以前のバージョンも確認できます。 | pending |
| `frontend:settings.profiles.at_version` | Version {{version}} | バージョン {{version}} | pending |
| `frontend:settings.profiles.basis` | Altmetric counts as | Altmetric の扱い | pending |
| `frontend:settings.profiles.basis_d28` | the score on day 28 | 28 日目のスコア | pending |
| `frontend:settings.profiles.basis_increase` | the increase from day 0 to day 28 | 0 日目から 28 日目までの増加 | pending |
| `frontend:settings.profiles.comparison_years` | Comparison set (academic years) | 比較対象（年度数） | pending |
| `frontend:settings.profiles.comparison_years_hint` | A release is compared with its own academic year and the ones before it. | リリースは、同じ年度とその前の年度のリリースと比較されます。 | pending |
| `frontend:settings.profiles.copy_of` | {{name}} (copy) | {{name}}（コピー） | pending |
| `frontend:settings.profiles.coverage_min` | Coverage needed (%) | 必要なカバー率（%） | pending |
| `frontend:settings.profiles.coverage_min_hint` | Below this share of its weight with values, a release gets no score: “insufficient data”. | 値のある要素の重みがこの割合を下回ると、スコアは算出されず「データ不足」となります。 | pending |
| `frontend:settings.profiles.create` | Create the profile | プロファイルを作成 | pending |
| `frontend:settings.profiles.default` | default | 既定 | pending |
| `frontend:settings.profiles.defaults_analysed_release_type_ids` | Analysed | 分析対象 | pending |
| `frontend:settings.profiles.defaults_help` | The release types the two Analysis filters start with. Analysed: what medians, ranks and every score are computed from. Shown: which of those appear. Nothing ticked means every type. Anyone can change both on the Analysis pages; this is only the starting point. | 分析ページの 2 つの絞り込みの初期値となるリリースの種類です。「分析対象」は中央値、順位、すべてのスコアの計算に使うリリース、「表示」はそのうち表示するリリースです。何も選ばないと、すべての種類が対象になります。分析ページでは誰でも変更でき、ここは初期値だけを決めます。 | pending |
| `frontend:settings.profiles.defaults_shown_release_type_ids` | Shown | 表示 | pending |
| `frontend:settings.profiles.defaults_title` | Where Analysis starts | 分析の初期設定 | pending |
| `frontend:settings.profiles.discard` | Discard changes | 変更を破棄 | pending |
| `frontend:settings.profiles.duplicate` | Duplicate | 複製 | pending |
| `frontend:settings.profiles.history` | Earlier versions ({{count}}) | 以前のバージョン（{{count}}） | pending |
| `frontend:settings.profiles.list` | Score profiles | スコアプロファイル | pending |
| `frontend:settings.profiles.make_default` | Make default | 既定にする | pending |
| `frontend:settings.profiles.manual` | How scores and profiles work | スコアとプロファイルの仕組み | pending |
| `frontend:settings.profiles.manual_heading` | Change a score profile | スコアプロファイルを変更する | pending |
| `frontend:settings.profiles.min_values` | Values needed per component | 要素ごとに必要な値の数 | pending |
| `frontend:settings.profiles.min_values_hint` | With fewer releases than this to compare with, a component does not count. | 比較できるリリースがこの数より少ない要素は、スコアに含めません。 | pending |
| `frontend:settings.profiles.name_en` | Name (English) | 名称（英語） | pending |
| `frontend:settings.profiles.name_ja` | Name (Japanese) | 名称（日本語） | pending |
| `frontend:settings.profiles.new` | New profile | 新しいプロファイル | pending |
| `frontend:settings.profiles.not_in_default` | Not in the default profile; other profiles can use it. | 既定のプロファイルには入れられません。他のプロファイルでは使えます。 | pending |
| `frontend:settings.profiles.now_default` | This is now the default profile. | このプロファイルを既定にしました。 | pending |
| `frontend:settings.profiles.preview` | Top 5 now | 現在の上位 5 件 | pending |
| `frontend:settings.profiles.preview_edited` | As edited | 編集中 | pending |
| `frontend:settings.profiles.preview_help` | The five finished releases with the highest score, with the default analysis filters below. | 下の分析の既定の絞り込みで、スコアが最も高い完了済みのリリース 5 件です。 | pending |
| `frontend:settings.profiles.preview_none` | No release has a score with these settings yet. | この設定では、まだスコアのあるリリースがありません。 | pending |
| `frontend:settings.profiles.preview_saved` | Saved (version {{version}}) | 保存済み（バージョン {{version}}） | pending |
| `frontend:settings.profiles.preview_score` | {{score}} · coverage {{coverage}} % | {{score}} ・ カバー率 {{coverage}} % | pending |
| `frontend:settings.profiles.purpose` | What it is for | 目的 | pending |
| `frontend:settings.profiles.rules` | Rules | ルール | pending |
| `frontend:settings.profiles.rules_summary` | Altmetric: {{basis}} · coverage {{coverage}} % · {{years}} academic years · {{values}} values | Altmetric：{{basis}} ・ カバー率 {{coverage}} % ・ {{years}} 年度 ・ {{values}} 件 | pending |
| `frontend:settings.profiles.save` | Save as a new version | 新しいバージョンとして保存 | pending |
| `frontend:settings.profiles.saved` | Saved as version {{version}}. | バージョン {{version}} として保存しました。 | pending |
| `frontend:settings.profiles.saved_by` | By | 保存者 | pending |
| `frontend:settings.profiles.saved_when` | Saved | 保存日時 | pending |
| `frontend:settings.profiles.system` | Release Radar | Release Radar | pending |
| `frontend:settings.profiles.total` | Total: {{total}} of 100 | 合計：{{total}} / 100 | pending |
| `frontend:settings.profiles.total_needed` | The weights must add up to 100 before you can save. | 保存するには、重みの合計を 100 にしてください。 | pending |
| `frontend:settings.profiles.unsaved` | Changed since version {{version}}, not saved yet. The draft is kept in this browser. | バージョン {{version}} から変更されていますが、まだ保存していません。下書きはこのブラウザに保存されます。 | pending |
| `frontend:settings.profiles.version` | Version | バージョン | pending |
| `frontend:settings.profiles.weights` | Weights | 重み | pending |
| `frontend:settings.profiles.weights_help` | How much each component counts. A component a release cannot have (no embargo, no pickups collected yet) leaves the sum, and the rest count for more. | 各要素をどれだけ重視するかです。リリースに存在しない要素（エンバーゴなし、まだ収集していない報道掲載など）は合計から外れ、残りの要素の比重が大きくなります。 | pending |
| `backend:analysis.dimensions.altmetric` | Altmetric (by the profile's basis) | Altmetric（プロファイルの基準による） | pending |
| `backend:analysis.dimensions.altmetric_increase` | Altmetric increase (day 28 − day 0) | Altmetric の増加（28 日目 − 0 日目） | pending |
| `backend:analysis.dimensions.inquiries` | Inquiries | 問い合わせ | pending |
| `backend:analysis.dimensions.inquiries_external` | Inquiries from outside the university | 学外からの問い合わせ | pending |
| `backend:analysis.dimensions.research_outcomes` | Research outcomes | 研究上の成果 | pending |
| `backend:analysis.dimensions.satisfaction` | Researcher satisfaction | 研究者の満足度 | pending |
| `backend:seed.profile.name` | News performance | ニュースでの反響 | pending |
| `backend:seed.profile.purpose` | How far a release travelled: news pickups, Altmetric, EurekAlert and the university's website, each compared with releases of the same and the two previous academic years. | リリースの広がり：ニュースでの掲載、Altmetric、EurekAlert、大学ウェブサイトの閲覧数を、同じ年度と前の 2 年度のリリースと比べます。 | pending |
