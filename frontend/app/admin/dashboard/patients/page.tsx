"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Search } from "lucide-react"

export default function PatientsPage() {
    const patients = [
        { id: 1, name: "Olivia Martin", email: "olivia.martin@email.com", lastVisit: "2024-02-28", condition: "Healthy" },
        { id: 2, name: "Jackson Lee", email: "jackson.lee@email.com", lastVisit: "2024-03-01", condition: "Hypertension" },
        { id: 3, name: "Isabella Nguyen", email: "isabella.nguyen@email.com", lastVisit: "2024-03-05", condition: "Flu Symptoms" },
    ]

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Patients</h2>
                    <p className="text-muted-foreground">View and manage patient records.</p>
                </div>
            </div>

            <div className="flex items-center space-x-2">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input className="pl-8" placeholder="Search patients..." />
                </div>
            </div>

            <div className="grid gap-4">
                {patients.map((patient) => (
                    <Card key={patient.id}>
                        <CardContent className="flex items-center justify-between p-6">
                            <div>
                                <p className="font-medium">{patient.name}</p>
                                <p className="text-sm text-muted-foreground">{patient.email}</p>
                            </div>
                            <div className="text-right">
                                <p className="text-sm font-medium">Last Visit: {patient.lastVisit}</p>
                                <p className="text-sm text-muted-foreground">{patient.condition}</p>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    )
}
