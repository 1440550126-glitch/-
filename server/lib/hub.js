// SSE 发布订阅中心：大厅、房间、个人通道
const channels = new Map(); // name -> Set<client>

export function subscribe(channel, client, userId = 0) {
  let set = channels.get(channel);
  if (!set) { set = new Set(); channels.set(channel, set); }
  client.userId = userId;
  set.add(client);
  client.onclose = () => {
    set.delete(client);
    if (!set.size) channels.delete(channel);
    client.onUnsub?.();
  };
  return () => { set.delete(client); if (!set.size) channels.delete(channel); };
}

export function publish(channel, event, data) {
  const set = channels.get(channel);
  if (!set) return 0;
  for (const c of set) c.send(event, data);
  return set.size;
}

export function publishTo(channel, userId, event, data) {
  const set = channels.get(channel);
  if (!set) return;
  for (const c of set) if (c.userId === userId) c.send(event, data);
}

export const listenerCount = (channel) => channels.get(channel)?.size || 0;
