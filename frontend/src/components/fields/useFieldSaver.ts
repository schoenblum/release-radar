import { useQueryClient, type QueryKey } from "@tanstack/react-query";

import { http } from "../../api/client";

/** Returns a function that saves one field of a record, then refreshes the listed data. */
export function useFieldSaver(path: string, ...invalidate: QueryKey[]) {
  const queryClient = useQueryClient();
  return (field: string) => async (value: unknown, version: number) => {
    const result = await http.patchField(path, field, value, version);
    await Promise.all(
      invalidate.map((queryKey) => queryClient.invalidateQueries({ queryKey })),
    );
    return result;
  };
}
