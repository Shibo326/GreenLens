import { useEffect } from 'react';
import { RouterProvider } from 'react-router';
import { Toaster } from 'sonner';
import { router } from './routes';
import { checkSession } from '../lib/api';
import { useAppState, useAppDispatch } from '../lib/store';

/**
 * On mount, silently verify the stored sessionId against the backend.
 * If the backend no longer knows about it (server restarted, session purged),
 * clear it from the store so the user gets a clean upload screen instead of
 * a confusing "session expired" error mid-chat.
 */
function SessionGuard() {
  const { sessionId } = useAppState();
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (!sessionId) return;

    checkSession(sessionId).then((valid) => {
      if (!valid) {
        console.info('[SessionGuard] Stored session no longer valid — clearing state');
        dispatch({ type: 'RESET' });
      }
    });
    // Only run once on mount — intentionally omit sessionId from deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}

export default function App() {
  return (
    <>
      <SessionGuard />
      <RouterProvider router={router} />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: 'var(--lead)',
            border: '1px solid var(--rule)',
            color: 'var(--paper)',
            fontFamily: "'IBM Plex Sans', 'Inter', sans-serif",
            fontSize: '14px',
          },
        }}
      />
    </>
  );
}
