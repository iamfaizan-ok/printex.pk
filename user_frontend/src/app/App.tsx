import React, { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import { Providers } from './providers';

export const App: React.FC = () => {
  useEffect(() => {
    try {
      const searchParams = new URLSearchParams(window.location.search);
      const shopParam = searchParams.get('shop') || searchParams.get('shop_id');
      if (shopParam) {
        localStorage.setItem('printx_shop_id', shopParam.trim());
      }
    } catch {
      // Ignored in SSR or sandbox environments
    }
  }, []);

  return (
    <Providers>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </Providers>
  );
};

export default App;
