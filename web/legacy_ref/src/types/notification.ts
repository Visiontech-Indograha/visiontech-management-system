export type NotificationType =
  | "DOCUMENT_EXPIRING"
  | "APPROVAL_PENDING"
  | "WORK_PLAN_DUE"
  | "LEAVE_APPROVED"
  | "LEAVE_REJECTED";

export interface NotificationResponse {
  id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  link: string | null;
  is_read: boolean;
  created_at: string;
}
