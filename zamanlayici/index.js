// GitHub'ın zamanlanmış işleri saatlerce gecikiyor ya da hiç çalışmıyor. Bu Worker, Cloudflare Cron ile
// 20 dakikada bir uyanıp iş akışlarını GitHub API'sinden zamanında başlatır (GH_TOKEN: Actions yazma izni).
const REPO = "cryptq55/nabiz26";

function due(now) {
  const h = now.getUTCHours(), m = now.getUTCMinutes();
  const jobs = [];
  if (m < 20 && h >= 5 && h <= 21 && h % 2 === 1) jobs.push("masa.yml");   // 08-24 TSİ, 2 saatte bir
  if (m < 20 && h === 6) jobs.push("altin.yml");                            // 09.00 TSİ
  if (m >= 20 && m < 40) jobs.push("foto.yml");                             // saatte bir
  return jobs;
}

async function dispatch(env, wf) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${wf}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "nabiz26-zamanlayici",
    },
    body: JSON.stringify({ ref: "main" }),
  });
  console.log(wf, r.status);
}

export default {
  async scheduled(event, env, ctx) {
    const jobs = due(new Date(event.scheduledTime));
    console.log("cron", new Date(event.scheduledTime).toISOString(), jobs.join(",") || "-");
    for (const wf of jobs) ctx.waitUntil(dispatch(env, wf));
  },
};
