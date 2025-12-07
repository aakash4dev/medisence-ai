"use client"

import { Card, CardContent } from "@/components/ui/card"
import { MessageSquare, User } from "lucide-react"

export default function MessagesPage() {
    const messages = [
        { id: 1, from: "Olivia Martin", subject: "Question about medication", preview: "Hi Dr. Smith, I was wondering if I should take the...", time: "10:30 AM", unread: true },
        { id: 2, from: "System", subject: "New Appointment Request", preview: "New appointment request from Jackson Lee for...", time: "09:15 AM", unread: false },
    ]

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-3xl font-bold tracking-tight">Messages</h2>
                <p className="text-muted-foreground">Communications from patients and system alerts.</p>
            </div>

            <div className="grid gap-4">
                {messages.map((msg) => (
                    <Card key={msg.id} className={msg.unread ? "border-l-4 border-l-primary" : ""}>
                        <CardContent className="flex items-start p-6 gap-4">
                            <div className="p-2 bg-slate-100 dark:bg-slate-800 rounded-full">
                                <MessageSquare className="h-5 w-5 text-slate-600 dark:text-slate-400" />
                            </div>
                            <div className="flex-1 space-y-1">
                                <div className="flex items-center justify-between">
                                    <p className={`font-medium ${msg.unread ? "text-foreground" : "text-muted-foreground"}`}>
                                        {msg.from}
                                    </p>
                                    <span className="text-xs text-muted-foreground">{msg.time}</span>
                                </div>
                                <p className="font-medium text-sm">{msg.subject}</p>
                                <p className="text-sm text-muted-foreground line-clamp-1">{msg.preview}</p>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    )
}
