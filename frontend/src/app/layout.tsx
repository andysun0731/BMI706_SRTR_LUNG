import type { Metadata } from 'next';
import './globals.css';
import Navigation from '@/components/Navigation';
import { Providers } from '@/components/Providers';

export const metadata: Metadata = {
    title: 'Lung Transplant Data Visualization',
    description: 'Interactive visualization of SRTR lung transplant data',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body>
                <Providers>
                    <div className="min-h-screen bg-slate-50">
                        <Navigation />
                        <main className="container mx-auto px-4 py-6">
                            {children}
                        </main>
                    </div>
                </Providers>
            </body>
        </html>
    );
}
