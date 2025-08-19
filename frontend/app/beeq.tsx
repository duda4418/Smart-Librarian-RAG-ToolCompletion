'use client';

import { useEffect, useState } from 'react';

interface BeeqSetupProps {
  children: React.ReactNode;
}

export default function BeeqSetup({ children }: BeeqSetupProps) {
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    import('@beeq/core/dist/components').then(({ setBasePath }) => {
      setBasePath('https://cdn.jsdelivr.net/npm/@beeq/core/dist/beeq/svg/');
      setIsInitialized(true);
    });
  }, []);

  if (!isInitialized) return null;

  return <>{children}</>;
}