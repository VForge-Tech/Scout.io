import { expect, test } from "vitest";

test("verify math sanity", () => {
  expect(1 + 1).toBe(2);
});

test("verify environment loading mock", () => {
  const mockApiUrl = "http://localhost:8000";
  expect(mockApiUrl).toContain("8000");
});
