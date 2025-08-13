/* global React, ReactDOM */
const { useEffect, useMemo, useState } = React;

// Telegram bridge
const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : undefined;

const useTelegram = () => {
  const webapp = tg;
  const themeParams = webapp?.themeParams ?? {};
  const color = (k, fallback) => themeParams?.[k] || fallback;
  const haptic = (type = "impact", style = "medium") => {
    try { webapp?.HapticFeedback?.impactOccurred?.(style); } catch {}
  };
  const notify = (text) => {
    try { webapp?.showToast?.(text); } catch { console.log(text); }
  };
  const share = (text, url) => {
    const shareUrl = url || (typeof location !== 'undefined' ? location.href : "");
    const tgLink = `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(text)}`;
    if (webapp?.openTelegramLink) return webapp.openTelegramLink(tgLink);
    if (navigator.share) return navigator.share({ title: "Support Mini App", text, url: shareUrl }).catch(()=>{});
    window.open(tgLink, "_blank");
  };
  return { webapp, themeParams, color, haptic, notify, share };
};

// Demo data
const samplePeople = [
  { id: 1, name: "Анна", age: 23, need: "Переезд в другой город, страшно начинать всё с нуля.", tags: ["тревога", "адаптация"], city: "Берлин" },
  { id: 2, name: "Иван", age: 30, need: "Выгорел на работе, нет сил, нужна моральная поддержка.", tags: ["выгорание"], city: "Кёльн" },
  { id: 3, name: "Лена", age: 19, need: "Сложная сессия, хочется, чтобы кто-то подбодрил.", tags: ["учёба"], city: "Мюнхен" },
  { id: 4, name: "Юра", age: 27, need: "Разрыв отношений, очень тяжело.", tags: ["отношения"], city: "Гамбург" },
];

const sampleTips = [
  "Поддержка — сначала слушать, потом советовать.",
  "Задавай открытые вопросы: 'Как ты себя чувствуешь?'",
  "Называй сильные стороны человека — это придаёт сил.",
  "Короткое тёплое сообщение лучше, чем долгий перфекционизм.",
];

const leagues = [
  { id: "bronze", name: "Бронзовая лига", color: "#b98c5e", from: 0, to: 49 },
  { id: "silver", name: "Серебряная лига", color: "#b0b7c3", from: 50, to: 199 },
  { id: "gold", name: "Золотая лига", color: "#ffcc66", from: 200, to: 499 },
  { id: "platinum", name: "Платиновая лига", color: "#7be0ff", from: 500, to: 9999 },
];

const AppStyles = () => (
  <style>{`
    :root{
      --bg: var(--tg-theme-bg-color, #ffffff);
      --text: var(--tg-theme-text-color, #1f2937);
      --hint: var(--tg-theme-hint-color, #6b7280);
      --btn: var(--tg-theme-button-color, #ec4899);
      --btn-text: var(--tg-theme-button-text-color, #ffffff);
      --card: var(--tg-theme-secondary-bg-color, #f8fafc);
      --ok: #10b981; --warn: #f59e0b; --danger: #ef4444;
      --muted: rgba(0,0,0,0.05);
      --shadow: 0 8px 24px rgba(0,0,0,.08);
      --radius: 16px; --radius-lg: 20px;
      --safe-bottom: env(safe-area-inset-bottom, 0px);
      --safe-top: env(safe-area-inset-top, 0px);
    }
    *{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
    html, body, #root { height: 100%; }
    body { margin: 0; font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "Helvetica Neue", Arial; background: var(--bg); color: var(--text); }
    .wrap { min-height: 100dvh; display: grid; grid-template-rows: 1fr auto; }
    .screen { padding: 16px; padding-top: calc(10px + var(--safe-top)); padding-bottom: calc(100px + var(--safe-bottom)); max-width: 540px; margin: 0 auto; width: 100%; }
    .row { display: flex; gap: 12px; align-items: center; }
    .col { display: flex; flex-direction: column; gap: 12px; }
    .card { background: var(--card); border-radius: var(--radius-lg); padding: 16px; box-shadow: var(--shadow); border: 1px solid rgba(0,0,0,.06); }
    .chip { font-size: 12px; padding: 8px 12px; border-radius: 999px; background: var(--muted); color: var(--hint); }
    .title { font-size: 22px; font-weight: 800; margin: 0 0 8px; }
    .subtitle { font-size: 14px; color: var(--hint); margin: -2px 0 10px; }
    .stat { background: #fff; border: 1px solid rgba(0,0,0,.06); border-radius: 18px; padding: 16px; flex: 1; min-height: 72px; display:flex; flex-direction:column; justify-content:center; }
    .stat .n { font-size: 22px; font-weight: 900; }
    .stat .l { font-size: 12px; color: var(--hint); }
    .btn { appearance: none; border: none; border-radius: 14px; padding: 14px 16px; background: linear-gradient(90deg,#06b6d4,#ec4899); color: var(--btn-text); font-weight: 800; cursor: pointer; box-shadow: var(--shadow); min-height: 48px; width: 100%; }
    .btn.ghost { background: transparent; color: var(--text); border: 1px solid rgba(0,0,0,.12); }
    .btn.ok { background: #10b981; }
    .btn.skip { background: transparent; border: 2px dashed rgba(0,0,0,.15); color: var(--hint); }
    .tabs { position: sticky; bottom: 0; left: 0; right: 0; background: #fff; border-top: 1px solid rgba(0,0,0,.08); display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; padding: 10px; padding-bottom: calc(10px + var(--safe-bottom)); }
    .tab { text-align: center; padding: 10px 6px; border-radius: 12px; color: var(--hint); font-size: 12px; min-height: 56px; display:flex; flex-direction:column; gap:2px; justify-content:center; align-items:center; }
    .tab.active { background: var(--muted); color: var(--text); font-weight: 800; }
    .tab .ico { font-size: 22px; }
    .avatar { width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #6a8dff, #b96bff); display:grid; place-items:center; font-weight:900; color: #fff; }
    .divider { height: 1px; background: rgba(0,0,0,.08); margin: 8px 0; }
    .swipe-card { position: relative; border-radius: 22px; overflow: hidden; background: var(--card); box-shadow: var(--shadow); }
    .swipe-header { position:absolute; top: 10px; left: 10px; right: 10px; display:flex; justify-content:space-between; pointer-events:none; }
    .swipe-badge { padding: 8px 12px; border-radius: 999px; background: rgba(0,0,0,.35); color: #fff; font-size: 12px; }
    .swipe-body { padding: 18px; min-height: 260px; display:flex; flex-direction:column; gap: 12px; justify-content: center; }
    .list { display: grid; gap: 10px; }
    .list-item { display:flex; align-items:center; gap: 12px; padding: 14px; background: var(--card); border-radius: 14px; border: 1px solid rgba(0,0,0,.06); }
    .time { font-size: 12px; color: var(--hint); }
    .leagues { display:grid; gap:12px; }
    .league-card { display:flex; align-items:center; justify-content:space-between; padding:16px; border-radius:18px; background: #fff; border:1px solid rgba(0,0,0,.06); }
    .field { display:flex; flex-direction:column; gap:6px; }
    .input { width: 100%; padding: 12px 14px; border-radius: 14px; border: 1px solid rgba(0,0,0,.12); background: #fff; color: var(--text); min-height: 48px; }
    textarea.input { min-height: 98px; resize: vertical; }
  `}</style>
);

const BottomTabs = ({ tab, setTab }) => {
  const items = [
    { key: "home", label: "Дом", icon: "🏠" },
    { key: "search", label: "Поиск", icon: "❤️" },
    { key: "notifications", label: "Уведомления", icon: "🔔" },
    { key: "leagues", label: "Лиги", icon: "🏆" },
    { key: "profile", label: "Профиль", icon: "👤" },
  ];
  return (
    <nav className="tabs" role="tablist" aria-label="Main tabs">
      {items.map((i) => (
        <button
          key={i.key}
          className={"tab" + (tab === i.key ? " active" : "")}
          onClick={() => setTab(i.key)}
          role="tab"
          aria-selected={tab === i.key}
        >
          <div className="ico" aria-hidden> {i.icon} </div>
          <div>{i.label}</div>
        </button>
      ))}
    </nav>
  );
};

function TelegramSupportMiniApp() {
  const { webapp, haptic, notify, share } = useTelegram();
  const [tab, setTab] = useState("home");
  const [queue, setQueue] = useState(samplePeople);
  const [sent, setSent] = useState([]);
  const [profile, setProfile] = useState({ nickname: "vasya", about: "Хочу поддерживать людей и делиться теплом.", city: "Берлин", score: 135 });

  const league = useMemo(() => leagues.find((l) => profile.score >= l.from && profile.score <= l.to) || leagues[0], [profile.score]);

  useEffect(() => {
    try {
      webapp?.ready();
      webapp?.expand?.();
      webapp?.setHeaderColor?.("secondary_bg_color");
    } catch {}
  }, [webapp]);

  useEffect(() => {
    if (!webapp?.BackButton) return;
    const BB = webapp.BackButton;
    if (tab !== "home") {
      BB.show();
      const handler = () => setTab("home");
      BB.onClick(handler);
      return () => { try { BB.offClick(handler); } catch {} };
    } else {
      BB.hide();
    }
  }, [tab, webapp]);

  useEffect(() => {
    const MB = webapp?.MainButton;
    if (!MB) return;
    MB.hide();
    MB.enable?.();

    if (tab === "profile") {
      MB.setText("Сохранить профиль");
      MB.show();
      const handler = () => { haptic(); notify("Профиль сохранён ✅"); };
      MB.onClick(handler);
      return () => { try { MB.offClick(handler); } catch {} };
    }

    if (tab === "search" && queue.length > 0) {
      MB.setText("Поддержать сейчас");
      MB.show();
      const handler = () => {
        haptic();
        notify("Напиши тёплые слова и нажми ‘Поддержать’");
        try { webapp?.showPopup?.({ title: "Совет", message: "Будь бережным. Короткое тёплое сообщение уже помогает." }); } catch {}
      };
      MB.onClick(handler);
      return () => { try { MB.offClick(handler); } catch {} };
    }
  }, [tab, queue.length, webapp, haptic, notify]);

  const skipPerson = () => {
    haptic();
    setQueue((q) => (q.length > 1 ? [...q.slice(1), q[0]] : q));
    notify("Показан следующий запрос");
  };

  const sendSupport = (toId, text) => {
    if (!text.trim()) { notify("Напиши сообщение"); return; }
    haptic();
    const msg = { toId, text: text.trim(), at: new Date().toISOString() };
    setSent((s) => [msg, ...s]);
    setQueue((q) => q.filter((p) => p.id !== toId));
    try { webapp?.HapticFeedback?.notificationOccurred?.("success"); } catch {}
    notify("Отправлено ✨");
  };

  const inviteFriend = () => {
    haptic();
    share("Залетай в мини‑приложение поддержки — напиши кому‑то тёплые слова!", undefined);
  };

  const openSettings = () => {
    haptic();
    if (webapp?.openLink) return webapp.openLink("https://t.me/BotFather");
    alert("Настройки — демо");
  };

  const Home = () => (
    <div className="screen col">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="row" style={{ gap: 12 }}>
          <div className="avatar">В</div>
          <div className="col" style={{ gap: 2 }}>
            <div style={{ fontWeight: 900, fontSize: 18 }}>Привет, Вася 👋</div>
            <div className="time">Лига: {league.name}</div>
          </div>
        </div>
        <span className="chip">v1.1</span>
      </div>

      <div className="row" style={{ gap: 12 }}>
        <div className="stat"><div className="n">{profile.score}</div><div className="l">Очков поддержки</div></div>
        <div className="stat"><div className="n">{sent.length}</div><div className="l">Сообщений сегодня</div></div>
      </div>

      <div className="card col" style={{ gap: 10 }}>
        <h3 className="title">Советы по поддержке</h3>
        {sampleTips.map((t,i)=> (
          <div key={i} className="row" style={{ gap: 10 }}>
            <span className="chip">#{i+1}</span>
            <div>{t}</div>
          </div>
        ))}
        <div className="row" style={{ gap: 10 }}>
          <button className="btn ok" onClick={() => { haptic(); setTab("search"); }}>Идти помогать</button>
          <button className="btn ghost" onClick={inviteFriend}>Пригласить друга</button>
        </div>
      </div>
    </div>
  );

  const Search = () => {
    const [text, setText] = useState("");
    const person = queue[0];
    return (
      <div className="screen col" style={{ gap: 12 }}>
        {person ? (
          <>
            <div className="swipe-card">
              <div className="swipe-header">
                <span className="swipe-badge">{person.city}</span>
                <span className="swipe-badge">{person.tags.join(" · ")}</span>
              </div>
              <div className="swipe-body">
                <div className="row" style={{ gap: 12, alignItems: "center" }}>
                  <div className="avatar">{person.name.charAt(0)}</div>
                  <div>
                    <div className="title" style={{ margin: 0 }}>{person.name}, {person.age}</div>
                    <div className="subtitle">нужна поддержка</div>
                  </div>
                </div>
                <div className="card" style={{ background: "#fff", border: "1px solid rgba(0,0,0,.06)" }}>
                  {person.need}
                </div>
                <div className="col">
                  <label className="field">
                    <span className="subtitle">Напиши короткое тёплое сообщение</span>
                    <textarea id="support-input" className="input" rows={4} placeholder="Я рядом. Ты не один/одна. Давай по шагу за раз…" value={text} onChange={(e) => setText(e.target.value)} />
                  </label>
                  <div className="col" style={{ gap: 8 }}>
                    <button className="btn ok" onClick={() => { sendSupport(person.id, text); setText(""); }}>Поддержать</button>
                    <div className="row" style={{ gap: 8 }}>
                      <button className="btn skip" onClick={skipPerson}>Пропустить</button>
                      <button className="btn ghost" onClick={() => { haptic(); share(`Поддержим ${person.name}?`, undefined); }}>Поделиться</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="subtitle">Совет: называй, что уже получилось у человека — это вселяет уверенность.</div>
          </>
        ) : (
          <div className="card col" style={{ alignItems: "center", textAlign: "center", gap: 10 }}>
            <div style={{ fontSize: 48 }}>🎉</div>
            <div className="title">Очередь пуста</div>
            <div className="subtitle">Пока никого рядом. Проверь позже или открой «Лиги».</div>
            <button className="btn" onClick={() => setTab("leagues")}>Открыть лиги</button>
          </div>
        )}
      </div>
    );
  };

  const Notifications = () => (
    <div className="screen col">
      <h3 className="title">Недавняя активность</h3>
      <div className="list">
        {sent.length === 0 && (
          <div className="card subtitle">Пока пусто. Поддержи кого-то в «Поиске», и здесь появится история.</div>
        )}
        {sent.map((m, i) => {
          const p = samplePeople.find((x) => x.id === m.toId);
          return (
            <div key={i} className="list-item" onClick={() => { navigator.clipboard?.writeText(m.text).then(()=>notify("Сообщение скопировано")); }}>
              <div className="avatar">{p?.name?.charAt(0) || "?"}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 800 }}>{p?.name || "Пользователь"}</div>
                <div className="time">{new Date(m.at).toLocaleString()}</div>
                <div style={{ marginTop: 6, color: "var(--hint)" }}>{m.text}</div>
              </div>
              <button className="btn ghost" style={{ width: 120 }} onClick={(e)=>{ e.stopPropagation(); haptic(); setTab("search"); }}>Ответить ещё</button>
            </div>
          );
        })}
      </div>
    </div>
  );

  const Leagues = () => (
    <div className="screen col">
      <h3 className="title">Лиги и рейтинг</h3>
      <div className="leagues">
        {leagues.map((l) => (
          <div key={l.id} className="league-card">
            <div className="col" style={{ gap: 4 }}>
              <div style={{ fontWeight: 900 }}>{l.name}</div>
              <div className="subtitle">{l.from}–{l.to === 9999 ? "∞" : l.to} очков</div>
            </div>
            <div className="row" style={{ gap: 8, alignItems: "center" }}>
              <div style={{ width: 18, height: 18, borderRadius: 5, background: l.color }} />
              <button className="btn ghost" style={{ width: 96 }} onClick={() => {
                haptic();
                const top = [
                  { nick: "@kindheart", score: 812 },
                  { nick: "@helper", score: 553 },
                  { nick: "@warm_words", score: 412 },
                ];
                const msg = top.map((t,i)=> `${i+1}. ${t.nick} — ${t.score}`).join("\n");
                try { tg?.showPopup?.({ title: "Топ недели", message: msg, buttons:[{type:'close'}]}); } catch { alert(msg); }
              }}>Топ</button>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <div className="title" style={{ margin: 0 }}>Твой рейтинг</div>
            <div className="subtitle">Ты в {league.name.toLowerCase()}. До следующей лиги: {Math.max(0, leagues.find(l=>l.id==="gold").from - profile.score)} очков</div>
          </div>
          <div className="chip">{profile.score} очков</div>
        </div>
        <div className="row" style={{ gap: 10, marginTop: 10 }}>
          <button className="btn" onClick={() => setTab("search")}>Поддержать кого‑то</button>
          <button className="btn ghost" onClick={inviteFriend}>Поделиться мини‑приложением</button>
        </div>
      </div>
    </div>
  );

  const Profile = () => (
    <div className="screen col" style={{ gap: 12 }}>
      <h3 className="title">Профиль</h3>
      <div className="row" style={{ gap: 12 }}>
        <div className="avatar" style={{ width: 64, height: 64, fontSize: 24 }}>В</div>
        <div className="col" style={{ gap: 6 }}>
          <div className="row" style={{ gap: 8, alignItems: "center" }}>
            <span style={{ fontWeight:900, fontSize:18 }}>@{profile.nickname}</span>
            <span className="chip">{league.name}</span>
          </div>
          <span className="time">Город: {profile.city}</span>
        </div>
      </div>

      <label className="field">
        <span className="subtitle">О себе</span>
        <textarea className="input" rows={4} value={profile.about} onChange={(e) => setProfile({ ...profile, about: e.target.value })} />
      </label>

      <div className="col" style={{ gap: 8 }}>
        <button className="btn" onClick={() => { haptic(); share("Мой профиль в Support Mini App"); }}>Поделиться профилем</button>
        <button className="btn ghost" onClick={openSettings}>Настройки</button>
      </div>

      <div className="divider" />
      <div className="subtitle">initData: {tg?.initDataUnsafe ? "получено" : "нет"} · платформа: {tg?.platform || "web"}</div>
    </div>
  );

  return (
    <div className="wrap">
      <AppStyles />
      {tab === "home" && <Home />}
      {tab === "search" && <Search />}
      {tab === "notifications" && <Notifications />}
      {tab === "leagues" && <Leagues />}
      {tab === "profile" && <Profile />}
      <BottomTabs tab={tab} setTab={(t)=>{ haptic(); setTab(t); }} />
    </div>
  );
}

// Auto-mount when loaded in a page with UMD React
if (typeof window !== "undefined") {
  window.TelegramSupportMiniApp = TelegramSupportMiniApp;
  const rootEl = document.getElementById("root");
  if (rootEl && window.ReactDOM?.createRoot) {
    ReactDOM.createRoot(rootEl).render(React.createElement(TelegramSupportMiniApp));
  }
}


