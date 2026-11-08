import { RouterProvider } from 'react-router';

import { ThemeProvider } from './contexts/ThemeContext';
import { router } from './app/routes';

// Light by default: the viva room and the showcase projector are lit spaces. The user's choice is remembered.
export default function App() {
  return (
    <ThemeProvider defaultTheme="light">
      <RouterProvider router={router} />
    </ThemeProvider>
  );
}
