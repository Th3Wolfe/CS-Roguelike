import { useCallback, useEffect, useState } from 'react';
import { getState } from '../api/client';

// Espelha o G global do index.html antigo, mas como estado React de verdade
// (sem mutação direta de DOM). refresh() pode ser chamado depois de qualquer
// ação que mude o estado no backend (jogar série, salvar, etc).
export function useGameState() {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await getState();
      setState(data.ok ? data : null); // ok:false = sem campanha em andamento
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { state, loading, error, refresh };
}
