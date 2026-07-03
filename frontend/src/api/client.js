// Cliente de API fino. Em dev, o vite.config.js faz proxy de /api pro Flask
// (porta 5000); em produção, front e back são servidos pela mesma origem,
// então esses paths relativos funcionam sem nenhuma mudança.

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin', // mantém o cookie de sessão do Flask
    ...options,
  });
  // O Flask sempre devolve JSON, mesmo em erros esperados (ex: 404 "Sem
  // jogo" quando ainda não existe uma campanha na sessão) — deixamos o
  // caller decidir o que fazer com `ok:false` em vez de tratar como exceção.
  let data;
  try {
    data = await res.json();
  } catch {
    throw new Error(`API ${path} devolveu resposta inválida (${res.status})`);
  }
  if (!res.ok && data?.ok === undefined) {
    // Erro de verdade (ex: 500) sem o formato {ok:false, error} esperado.
    throw new Error(`API ${path} falhou (${res.status})`);
  }
  return data;
}

export function getState() {
  return request('/api/state');
}

export function get(path) {
  return request(path);
}

export function post(path, body) {
  return request(path, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}
