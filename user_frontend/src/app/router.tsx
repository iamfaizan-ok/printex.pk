import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '../components/layout/MainLayout';
import { HomePage } from '../pages/HomePage';
import { UploadPage } from '../pages/UploadPage';
import { PrintSettingsPage } from '../pages/PrintSettingsPage';
import { ReviewOrderPage } from '../pages/ReviewOrderPage';
import { PaymentComingSoonPage } from '../pages/PaymentComingSoonPage';
import { NotFoundPage } from '../pages/NotFoundPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'upload',
        element: <UploadPage />,
      },
      {
        path: 'print-settings',
        element: <PrintSettingsPage />,
      },
      {
        path: 'review-order',
        element: <ReviewOrderPage />,
      },
      {
        path: 'payment-coming-soon',
        element: <PaymentComingSoonPage />,
      },
      {
        path: '404',
        element: <NotFoundPage />,
      },
      {
        path: '*',
        element: <Navigate to="/404" replace />,
      },
    ],
  },
], {
  future: {
    v7_relativeSplatPath: true,
  },
});
