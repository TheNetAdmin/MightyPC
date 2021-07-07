#
# This is a Shiny web application. You can run the application by clicking
# the 'Run App' button above.
#
# Find out more about building applications with Shiny here:
#
#    http://shiny.rstudio.com/
#

library(shiny)
library(mongolite)
library(dplyr)
library(DT)

# Define UI for application that draws a histogram
ui <- fluidPage(

    # Application title
    titlePanel("MightyPC - Mighty Program Chair Toolkit"),

    uiOutput('select_author_id'),

    hr(),
    h3(textOutput("submission_title")),
    sidebarLayout(
        sidebarPanel(
            h4("Info"),
            fluidRow(
                column(width=3, tableOutput('submission_tags')),
                column(width=9, tableOutput('submission_authors'))
            )
        ),
        mainPanel(
            h4("Abstract"),
            textOutput("submission_abstract"),
       ),
    ),
    tabsetPanel(type = 'tabs',
                tabPanel('Summary', fluidRow(
                    column(width=4, h2('Potential Reviewers'), DTOutput('submission_potential_reviewers')),
                    column(width=6, h2('Cited PC Papers'), DTOutput("submission_reference_pc_no_conflict")),
                    column(width=2, h2('ML Suggested Reviewers'), DTOutput('submission_ml_suggested_reviewers'))
                )),
                tabPanel('Reviewers', DTOutput('submission_potential_reviewers_standalone')),
                tabPanel('References No Conflict', DTOutput("submission_reference_pc_no_conflict_standalone")),
                tabPanel('References', DTOutput("submission_reference")),
                tabPanel('Tags', DTOutput("submission_tag_check"))
                )
)


server <- function(input, output) {

    # NOTE: set your mongodb username, password and url:port
    sdb = mongo(collection = 'submission', db = 'hotcrp', url = 'mongodb://USERNAME:PASSWORD@URL:PORT')

    submission <- sdb$find(fields = '{"_id": 1}')
    submission_ids <- submission[,1]
    submission_ids <- sort(submission_ids)
    submission_ids <- as.list(submission_ids)
    output$select_author_id = renderUI({
        selectInput(
        "selected_submission_id",
        label = h3("Select Submission ID"),
        choices=submission_ids,
        selected = 1
        )
    })


    record <- reactive({ sdb$find(query = paste('{"_id":', input$selected_submission_id, '}')) })

    output$submission_title <- renderText({ record()$title })

    output$submission_abstract <- renderText({ record()$abstract })

    output$submission_authors <- renderTable({
        data.frame(record()$authors) %>%
            select(first, last, affiliation)
    })

    output$submission_tags <- renderTable({
        t <- data.frame(record()$tags, stringsAsFactors = FALSE)
        colnames(t) <- c('Tags')
        t
    }, options = list(pageLength = 4, lengthChange = FALSE), rownames= FALSE)

    output$submission_tag_check <- renderDT({
        data.frame(record()$tag_check) %>%
            relocate(tag_name)
    }, options = list(pageLength = 50), colnames = FALSE, rownames= FALSE)

    output$submission_reference <- renderDT({
        data.frame(record()$reference) %>%
            rowwise() %>%
            mutate(PCAuthor = ifelse("mag_record" %in% names(.), paste(data.frame(mag_record$PCAuthor)$name, collapse = ', '), '')) %>%
            mutate(tpc_no_conflict = ifelse("tpc_no_conflict" %in% names(.), paste(data.frame(tpc_no_conflict)$name, collapse = ', '), '')) %>%
            mutate(erc_no_conflict = ifelse("erc_no_conflict" %in% names(.), paste(data.frame(erc_no_conflict)$name, collapse = ', '), '')) %>%
            mutate(linemarker = as.numeric(linemarker)) %>%
            select(linemarker, title, count, pc_paper, PCAuthor, pc_paper_no_conflict, tpc_no_conflict, erc_no_conflict)
    }, options = list(pageLength = 50), rownames= FALSE)

    output$submission_reference_pc_no_conflict <- renderDT({
        data.frame(record()$reference) %>%
            rowwise() %>%
            # filter('pc_paper' %in% names(.)) %>%
            filter(pc_paper_no_conflict == TRUE) %>%
            mutate(linemarker = as.numeric(linemarker)) %>%
            mutate(tpc_no_conflict = ifelse("tpc_no_conflict" %in% names(.), paste(data.frame(tpc_no_conflict)$name, collapse = ', '), '')) %>%
            mutate(erc_no_conflict = ifelse("erc_no_conflict" %in% names(.), paste(data.frame(erc_no_conflict)$name, collapse = ', '), '')) %>%
            select(title, count, tpc_no_conflict, erc_no_conflict) %>%
            arrange(desc(count))

    }, options = list(pageLength = 25), rownames= FALSE)


    output$submission_reference_pc_no_conflict_standalone <-  renderDT({
        data.frame(record()$reference) %>%
            rowwise() %>%
            # filter('pc_paper' %in% names(.)) %>%
            filter(pc_paper_no_conflict == TRUE) %>%
            mutate(linemarker = as.numeric(linemarker)) %>%
            mutate(tpc_no_conflict = ifelse("tpc_no_conflict" %in% names(.), paste(data.frame(tpc_no_conflict)$name, collapse = ', '), '')) %>%
            mutate(erc_no_conflict = ifelse("erc_no_conflict" %in% names(.), paste(data.frame(erc_no_conflict)$name, collapse = ', '), '')) %>%
            select(linemarker, title, count, pc_paper_no_conflict, tpc_no_conflict, erc_no_conflict) %>%
            arrange(desc(count))

    }, options = list(pageLength = 50), rownames= FALSE)

    output$submission_ml_suggested_reviewers <- renderDT({
        s <- data.frame(record()$ml_suggested_reviewers)
        colnames(s) <- c('ML Suggested Reviewers')
        s
    }, options = list(pageLength = 25), rownames= FALSE)

    output$submission_potential_reviewers <- renderDT({
        data.frame(record()$potential_reviewers) %>%
            select(name, pc_type, count_cited) %>%
            arrange(desc(count_cited)) %>%
            arrange(desc(pc_type))
    }, options = list(pageLength = 25), rownames= FALSE)

    output$submission_potential_reviewers_standalone <- renderDT({
        data.frame(record()$potential_reviewers) %>%
            select(name, email, affiliation,  pc_type, count_paper, count_cited) %>%
            arrange(desc(count_cited))
    }, options = list(pageLength = 50), rownames= FALSE)
}

# Run the application
shinyApp(ui = ui, server = server)
