import { useQuery } from "@tanstack/react-query";
import { fetchParks } from "../api/parks";

export function useParks() {
  return useQuery({
    queryKey: ["parks"],
    queryFn: fetchParks,
  });
}
