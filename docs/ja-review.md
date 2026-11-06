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
