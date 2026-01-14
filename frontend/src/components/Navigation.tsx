'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const tabs = [
    { name: 'Map', href: '/' },
    { name: 'Survival', href: '/survival' },
    { name: 'Utilization', href: '/utilization' },
];

export default function Navigation() {
    const pathname = usePathname();

    return (
        <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-200/50">
            <div className="max-w-6xl mx-auto px-6">
                <div className="flex items-center justify-between h-12">
                    {/* Logo */}
                    <Link href="/" className="flex items-center">
                        <span className="text-[17px] font-semibold text-[#1d1d1f]">
                            Lung Transplant
                        </span>
                    </Link>

                    {/* Navigation Tabs */}
                    <div className="flex items-center space-x-8">
                        {tabs.map((tab) => {
                            const isActive = pathname === tab.href;
                            return (
                                <Link
                                    key={tab.name}
                                    href={tab.href}
                                    className={`
                    text-[12px] font-normal transition-colors duration-200
                    ${isActive
                                            ? 'text-[#1d1d1f]'
                                            : 'text-[#86868b] hover:text-[#1d1d1f]'
                                        }
                  `}
                                >
                                    {tab.name}
                                </Link>
                            );
                        })}
                    </div>
                </div>
            </div>
        </nav>
    );
}
