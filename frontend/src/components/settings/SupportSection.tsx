"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { SettingsCard, SettingsSectionHeader } from "./settingsChrome"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as supportApi from "@/lib/support/supportApi"
import { type SupportRequestFormValues, supportRequestSchema } from "@/lib/validation"
import { useReportStore } from "@/store/reportStore"

/**
 * FR-027 (Milestone 3) -- Care Team support request. A plain settings
 * form, not a chat surface: deliberately distinct in both location and
 * visual pattern from the AI Beauty Assistant so a user is never confused
 * about whether they're messaging a person or a model (a real person
 * follows up by email). The current report id, if any, is auto-attached
 * from useReportStore -- never a form field the user has to fill in
 * themselves.
 */
export function SupportSection() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const reportId = useReportStore((state) => state.report?.id)

  const form = useForm<SupportRequestFormValues>({
    resolver: zodResolver(supportRequestSchema),
    defaultValues: { subject: "", message: "" },
    mode: "onBlur",
  })

  async function onSubmit(values: SupportRequestFormValues) {
    setIsSubmitting(true)
    try {
      await supportApi.submitSupportRequest(values.subject, values.message, reportId)
      toast.success("Your request has been sent. Our team will follow up by email.")
      form.reset()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleCancel() {
    form.reset()
  }

  return (
    <div className="w-full space-y-5">
      <SettingsSectionHeader
        title="Contact Us"
        description="Message our care team directly -- a person will follow up by email, not an AI."
      />

      <SettingsCard>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-4">
            <FormField
              control={form.control}
              name="subject"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm">Subject</FormLabel>
                  <FormControl>
                    <Input placeholder="What's this about?" disabled={isSubmitting} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="message"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm">Message</FormLabel>
                  <FormControl>
                    <Textarea
                      rows={5}
                      placeholder="Tell us what's on your mind."
                      disabled={isSubmitting}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex gap-2.5 pt-1">
              <Button
                type="button"
                variant="outline"
                className="h-10 flex-1 rounded-full"
                onClick={handleCancel}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" className="h-10 flex-1 rounded-full" disabled={isSubmitting}>
                {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : null}
                Send
              </Button>
            </div>
          </form>
        </Form>
      </SettingsCard>
    </div>
  )
}
