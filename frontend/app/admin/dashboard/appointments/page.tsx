"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Calendar as CalendarIcon, Clock, User } from "lucide-react"

export default function AppointmentsPage() {
    // Mock data
    const appointments = [
        { id: 1, patient: "Olivia Martin", time: "09:00 AM", date: "2024-03-10", type: "General Checkup", status: "Confirmed" },
        { id: 2, patient: "Jackson Lee", time: "10:30 AM", date: "2024-03-10", type: "Follow-up", status: "Confirmed" },
        { id: 3, patient: "Isabella Nguyen", time: "02:00 PM", date: "2024-03-10", type: "Symptom Review", status: "Pending" },
        { id: 4, patient: "William Chen", time: "04:15 PM", date: "2024-03-10", type: "Consultation", status: "Cancelled" },
    ]

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Appointments</h2>
                    <p className="text-muted-foreground">Manage your schedule and patient visits.</p>
                </div>
                <Button>
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    New Appointment
                </Button>
            </div>

            <div className="grid gap-4">
                {appointments.map((apt) => (
                    <Card key={apt.id}>
                        <CardContent className="flex items-center p-6">
                            <div className="flex items-center space-x-4 flex-1">
                                <div className="p-2 bg-primary/10 rounded-full text-primary">
                                    <User className="h-6 w-6" />
                                </div>
                                <div>
                                    <p className="font-medium">{apt.patient}</p>
                                    <p className="text-sm text-muted-foreground">{apt.type}</p>
                                </div>
                            </div>

                            <div className="flex items-center space-x-8 mr-8">
                                <div className="flex items-center text-sm text-muted-foreground">
                                    <CalendarIcon className="mr-2 h-4 w-4" />
                                    {apt.date}
                                </div>
                                <div className="flex items-center text-sm text-muted-foreground">
                                    <Clock className="mr-2 h-4 w-4" />
                                    {apt.time}
                                </div>
                            </div>

                            <div className={`px-3 py-1 rounded-full text-xs font-medium ${apt.status === 'Confirmed' ? 'bg-green-100 text-green-700' :
                                    apt.status === 'Pending' ? 'bg-yellow-100 text-yellow-700' :
                                        'bg-red-100 text-red-700'
                                }`}>
                                {apt.status}
                            </div>

                            <div className="ml-6">
                                <Button variant="ghost" size="sm">Edit</Button>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    )
}
