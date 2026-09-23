export enum UserRole {
  ADMIN = "ADMIN",
  HR_HES = "HR_HES",
  FINANCE = "FINANCE",
  PM = "PM",
  OM = "OM",
  FIELD_STAFF = "FIELD_STAFF",
}

export interface UserApp {
  id: string;
  username: string;
  role: UserRole;
  employee_id?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface TokenPayload {
  sub: string;
  role: string;
  exp: number;
}
