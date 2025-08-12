import React from "react"
import { Container, Heading, HStack, Stack, Table, Button, Text } from "@chakra-ui/react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { OpenAPI } from "@/client/core/OpenAPI"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/scraper")({
  component: ScraperPage,
})

const API_PREFIX = "/api/v1"

function apiUrl(path: string) {
  const base = (OpenAPI.BASE || "").replace(/\/$/, "")
  return base + path
}

async function listPosts(params: { company?: string; platform?: string }) {
  const url = new URL(apiUrl(`${API_PREFIX}/scraper/posts/`))
  if (params.company) url.searchParams.set("company", params.company)
  if (params.platform) url.searchParams.set("platform", params.platform)
  const res = await fetch(url.toString(), { credentials: "include" })
  if (!res.ok) throw new Error(`Failed to fetch posts: ${res.status}`)
  return (await res.json()) as { data: any[]; count: number }
}

async function runScraper(companies: string[]) {
  const url = new URL(apiUrl(`${API_PREFIX}/scraper/run/`))
  for (const c of companies) url.searchParams.append("companies", c)
  const res = await fetch(url.toString(), { method: "POST", credentials: "include" })
  if (!res.ok) {
    const txt = await res.text()
    throw new Error(`Run failed: ${res.status} ${txt}`)
  }
  return res.json()
}

function downloadCSV(filename: string, rows: any[]) {
  const headers = ["company", "platform", "title", "url", "score", "published_at"]
  const csv = [headers.join(","), ...rows.map((r) => headers.map((h) => JSON.stringify(r[h] ?? "")).join(","))].join("\n")
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const link = document.createElement("a")
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

function ScraperPage() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [company, setCompany] = React.useState<string>("")
  const [platform, setPlatform] = React.useState<string>("")
  const [sortBy, setSortBy] = React.useState<string>("published_desc")
  const [autoRefresh, setAutoRefresh] = React.useState<boolean>(false)
  const companies = ["laudite", "laudos.ai", "laudos", "leorad"]

  const postsQuery = useQuery({ queryKey: ["scraped-posts", { company, platform }], queryFn: () => listPosts({ company: company || undefined, platform: platform || undefined }) })

  React.useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(() => postsQuery.refetch(), 60_000)
    return () => clearInterval(id)
  }, [autoRefresh, postsQuery.refetch])

  const runMutation = useMutation({
    mutationFn: (payload: string[]) => runScraper(payload),
    onSuccess: () => {
      showSuccessToast("Scrape triggered")
      postsQuery.refetch()
    },
    onError: (err: any) => {
      showErrorToast(String(err?.message || err))
    },
  })

  const sorted = React.useMemo(() => {
    const data = postsQuery.data?.data ?? []
    const copy = [...data]
    switch (sortBy) {
      case "score_desc":
        copy.sort((a, b) => (b.score ?? -1) - (a.score ?? -1))
        break
      case "title_asc":
        copy.sort((a, b) => String(a.title || "").localeCompare(String(b.title || "")))
        break
      default:
        copy.sort((a, b) => new Date(b.published_at || 0).getTime() - new Date(a.published_at || 0).getTime())
    }
    return copy
  }, [postsQuery.data, sortBy])

  return (
    <Container maxW="full">
      <Stack gap={6} pt={12}>
        <Heading size="lg">Scraper</Heading>

        <HStack gap={4} wrap="wrap">
          {companies.map((c) => (
            <Button key={c} onClick={() => runMutation.mutate([c])} loading={runMutation.isPending}>
              Scrape {c}
            </Button>
          ))}
          <Button onClick={() => runMutation.mutate(companies)} variant="outline" loading={runMutation.isPending}>
            Scrape All
          </Button>
        </HStack>

        <HStack gap={4} align="flex-end" wrap="wrap">
          <select value={company} onChange={(e) => setCompany(e.target.value)} style={{ padding: 8 }}>
            <option value="">All companies</option>
            <option value="laudite">laudite</option>
            <option value="laudos.ai">laudos.ai</option>
            <option value="laudos">laudos</option>
            <option value="leorad">leorad</option>
          </select>
          <select value={platform} onChange={(e) => setPlatform(e.target.value)} style={{ padding: 8 }}>
            <option value="">All platforms</option>
            <option value="website">website</option>
          </select>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} style={{ padding: 8 }}>
            <option value="published_desc">Sort: Newest</option>
            <option value="score_desc">Sort: Score</option>
            <option value="title_asc">Sort: Title</option>
          </select>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} /> Auto refresh (60s)
          </label>
          <Button
            variant="outline"
            onClick={() => downloadCSV(`scraped-posts-${Date.now()}.csv`, sorted)}
            disabled={!sorted?.length}
          >
            Export CSV
          </Button>
          <Button onClick={() => postsQuery.refetch()} loading={postsQuery.isFetching}>
            Refresh
          </Button>
          <Text color="gray.500">{sorted.length} items</Text>
        </HStack>

        <Table.Root size={{ base: "sm", md: "md" }}>
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeader w="sm">Company</Table.ColumnHeader>
              <Table.ColumnHeader w="sm">Platform</Table.ColumnHeader>
              <Table.ColumnHeader w="md">Title</Table.ColumnHeader>
              <Table.ColumnHeader w="xs">Score</Table.ColumnHeader>
              <Table.ColumnHeader w="sm">Published</Table.ColumnHeader>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {sorted.map((p) => (
              <Table.Row key={p.id}>
                <Table.Cell>{p.company}</Table.Cell>
                <Table.Cell>{p.platform}</Table.Cell>
                <Table.Cell>
                  <a href={p.url} target="_blank" rel="noreferrer">
                    {p.title || p.url}
                  </a>
                </Table.Cell>
                <Table.Cell>{p.score ?? "-"}</Table.Cell>
                <Table.Cell>{p.published_at ? new Date(p.published_at).toLocaleString() : "-"}</Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      </Stack>
    </Container>
  )
}
