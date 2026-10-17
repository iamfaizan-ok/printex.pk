import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import { Providers } from './providers';

export const App: React.FC = () => {
  return (
    <Providers>
      <RouterProvider router={router} future={{ v7_startTransition: true }} />
    </Providers>
  );
};

export default App;
