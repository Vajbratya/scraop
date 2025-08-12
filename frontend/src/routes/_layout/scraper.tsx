import {
  Button,
  Container,
  HStack,
  Heading,
  Stack,
  Table,
} from "@chakra-ui/react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import React from "react"

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
  const res = await fetch(url.toString(), {
    method: "POST",
    credentials: "include",
  })
  if (!res.ok) {
    const txt = await res.text()
    throw new Error(`Run failed: ${res.status} ${txt}`)
  }
  return res.json()
}

function ScraperPage() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [company, setCompany] = React.useState<string>("")
  const [platform, setPlatform] = React.useState<string>("")
  const companies = ["laudite", "laudos.ai", "laudos", "leorad"]

  const postsQuery = useQuery({
    queryKey: ["scraped-posts", { company, platform }],
    queryFn: () =>
      listPosts({
        company: company || undefined,
        platform: platform || undefined,
      }),
  })

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

  return (
    <Container maxW="full">
      <Stack gap={6} pt={12}>
        <Heading size="lg">Scraper</Heading>

        <HStack gap={4} wrap="wrap">
          {companies.map((c) => (
            <Button
              key={c}
              onClick={() => runMutation.mutate([c])}
              loading={runMutation.isPending}
            >
              Scrape {c}
            </Button>
          ))}
          <Button
            onClick={() => runMutation.mutate(companies)}
            variant="outline"
            loading={runMutation.isPending}
          >
            Scrape All
          </Button>
        </HStack>

        <HStack gap={4} align="flex-end" wrap="wrap">
          <select
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            style={{ padding: 8 }}
          >
            <option value="">All companies</option>
            <option value="laudite">laudite</option>
            <option value="laudos.ai">laudos.ai</option>
            <option value="laudos">laudos</option>
            <option value="leorad">leorad</option>
          </select>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            style={{ padding: 8 }}
          >
            <option value="">All platforms</option>
            <option value="website">website</option>
          </select>
          <Button
            onClick={() => postsQuery.refetch()}
            loading={postsQuery.isFetching}
          >
            Refresh
          </Button>
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
            {postsQuery.data?.data?.map((p) => (
              <Table.Row key={p.id}>
                <Table.Cell>{p.company}</Table.Cell>
                <Table.Cell>{p.platform}</Table.Cell>
                <Table.Cell>
                  <a href={p.url} target="_blank" rel="noreferrer">
                    {p.title || p.url}
                  </a>
                </Table.Cell>
                <Table.Cell>{p.score ?? "-"}</Table.Cell>
                <Table.Cell>
                  {p.published_at
                    ? new Date(p.published_at).toLocaleString()
                    : "-"}
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      </Stack>
    </Container>
  )
}
