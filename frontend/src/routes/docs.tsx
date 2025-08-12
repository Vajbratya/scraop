import { OpenAPI } from "@/client/core/OpenAPI"
import { Box, Center, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/docs")({
  component: DocsPage,
})

function DocsPage() {
  const base = (OpenAPI.BASE || "").replace(/\/$/, "")
  const src = base ? `${base}/docs` : "/docs"
  return (
    <Box h="calc(100vh - 80px)" w="100%">
      <iframe
        title="API Docs"
        src={src}
        style={{ width: "100%", height: "100%", border: 0 }}
      />
      {!base && (
        <Center position="absolute" bottom={2} left={0} right={0}>
          <Text fontSize="xs" color="gray.500">
            If docs don't load in dev, set VITE_API_URL to your backend URL.
          </Text>
        </Center>
      )}
    </Box>
  )
}
