async function jsonFetch(url, options) {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `HTTP ${resp.status}`);
  }
  if (resp.status === 204) return null;
  return await resp.json();
}

function setStatus(el, message, ok) {
  el.textContent = message;
  el.className = `status ${ok ? "ok" : "err"}`;
}

function renderServers(items) {
  const list = document.getElementById("serverList");
  list.innerHTML = "";
  for (const s of items) {
    const li = document.createElement("li");
    li.textContent = `${s.name} (${s.id}) -> ${s.base_url}${s.mcp_endpoint}`;
    list.appendChild(li);
  }
}

function renderExample(serverId) {
  const block = document.getElementById("exampleBlock");
  block.textContent = JSON.stringify(
    {
      endpoint: "/mcp/",
      headers: { "x-mcp-server-id": serverId || "<server_id>" },
      body: {
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          clientInfo: { name: "demo-client" },
          capabilities: {}
        }
      }
    },
    null,
    2
  );
}

async function refreshServers() {
  const items = await jsonFetch("/api/servers");
  renderServers(items);
  renderExample(items[0]?.id);
}

async function createServer() {
  const status = document.getElementById("createStatus");
  try {
    await jsonFetch("/api/servers", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: document.getElementById("name").value,
        base_url: document.getElementById("base_url").value,
        mcp_endpoint: document.getElementById("mcp_endpoint").value,
        description: document.getElementById("description").value,
        tags: ["demo"],
        headers: {}
      })
    });
    setStatus(status, "Created", true);
    await refreshServers();
  } catch (err) {
    setStatus(status, String(err), false);
  }
}

document.getElementById("createBtn").addEventListener("click", createServer);
document.getElementById("refreshBtn").addEventListener("click", refreshServers);

refreshServers().catch(() => renderExample());
