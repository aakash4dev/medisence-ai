import Link from "next/link"
import { LayoutDashboard, Users, Calendar, MessageSquare, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <div className="min-h-screen flex bg-slate-50 dark:bg-slate-950">
            {/* Sidebar */}
            <aside className="w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 hidden md:flex flex-col">
                <div className="p-6 border-b border-slate-200 dark:border-slate-800">
                    <h1 className="text-xl font-bold flex items-center gap-2">
                        <span className="text-primary">MedicSense</span> Admin
                    </h1>
                </div>

                <nav className="flex-1 p-4 space-y-2">
                    <Link href="/admin/dashboard" className="flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-md bg-primary/10 text-primary">
                        <LayoutDashboard className="w-5 h-5" />
                        Overview
                    </Link>
                    <Link href="/admin/dashboard/appointments" className="flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-md text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800">
                        <Calendar className="w-5 h-5" />
                        Appointments
                    </Link>
                    <Link href="/admin/dashboard/patients" className="flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-md text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800">
                        <Users className="w-5 h-5" />
                        Patients
                    </Link>
                    <Link href="/admin/dashboard/messages" className="flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-md text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800">
                        <MessageSquare className="w-5 h-5" />
                        Messages
                    </Link>
                </nav>

                <div className="p-4 border-t border-slate-200 dark:border-slate-800">
                    <Link href="/admin/login">
                        <Button variant="outline" className="w-full justify-start gap-2">
                            <LogOut className="w-4 h-4" />
                            Sign Out
                        </Button>
                    </Link>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto">
                <div className="p-8">
                    {children}
                </div>
            </main>
        </div>
    )
}
