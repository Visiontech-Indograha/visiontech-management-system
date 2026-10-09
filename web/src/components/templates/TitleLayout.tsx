import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { pageTitle } from "@/app/pageTitle";

/** Layout tanpa tampilan: menyetel `document.title` mengikuti rute, lalu merender halamannya. */
export function TitleLayout() {
  const { pathname } = useLocation();
  useEffect(() => {
    document.title = pageTitle(pathname);
  }, [pathname]);
  return <Outlet />;
}
